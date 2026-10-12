#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy K마켙 (`ecommerce-ontology`) 3-Plane Architecture to live GCP (`finance-ontology-changseop`):
  - S04: GCS bucket `gs://kmarket_okf/okf/` + Dataplex EntryGroup `ecommerce-okf` (82 entries)
  - S05: Spanner DB `finance-cs/kmarket_ecommerce` (5 tables, 70 rows) +
         BigQuery `kmarket_ecommerce` (3 master tables, 98 rows) +
         BigQuery External Schema `kmarket_ecommerce_ext` + 5 `ont_*` federated views
  - S06: BigQuery ObjectRef connection `us-central1.okf-gcs-conn` IAM binding on `gs://kmarket_okf`
  - S07: BigQuery `kmarket_ontology` (LEX/CTX/Bridge/Alias tables + 11 Node Views + 15 Edge Views +
         PROPERTY GRAPH `kmarket_ontology.ecommerce_graph`) +
         Dataplex Glossary `kmarket-ecommerce-glossary` (7 terms) +
         KC `ontology-class-anchors` Aspect on `@bigquery` graph entry.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import datetime as _dt
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import google.auth
from google.auth.transport.requests import Request
from google.cloud import bigquery, spanner, storage
import yaml

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ECOM_DIR = os.path.join(ROOT, "ecommerce")
CSV_DIR = os.path.join(ECOM_DIR, "data", "structured")
OKF_DIR = os.path.join(ECOM_DIR, "okf")
VERIFICATION_JSON = os.path.join(OKF_DIR, "verification.json")
L1_YAML = os.path.join(ECOM_DIR, "ontology", "l1.yaml")
SPANNER_DDL_PATH = os.path.join(ECOM_DIR, "sql", "spanner_kmarket_ecommerce.ddl")
GRAPH_SQL_PATH = os.path.join(ECOM_DIR, "sql", "bigquery_ecommerce_graph.sql")

PROJECT = "finance-ontology-changseop"
PROJECT_NUMBER = "567090080191"
LOCATION = "us-central1"
SPANNER_INSTANCE = "finance-cs"
SPANNER_DATABASE = "kmarket_ecommerce"
SRC_DS = "kmarket_ecommerce"
EXT_DS = "kmarket_ecommerce_ext"
ONT_DS = "kmarket_ontology"
GRAPH_NAME = "ecommerce_graph"
BUCKET = "kmarket_okf"
PREFIX = "okf"
ENTRY_GROUP = "ecommerce-okf"
ENTRY_TYPE = "okf-bundle"
GLOSSARY_ID = "kmarket-ecommerce-glossary"
ANCHOR_ASPECT_ID = "ontology-class-anchors"

OKF_ASPECT = f"{PROJECT_NUMBER}.{LOCATION}.okf"
OVERVIEW_ASPECT = "dataplex-types.global.overview"


def get_token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(Request())
    return creds.token


def rest_request(
    method: str,
    url: str,
    token: str,
    payload: dict | None = None,
    ignore_status: tuple[int, ...] = (),
) -> tuple[int, dict]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        if e.code in ignore_status:
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"raw": raw}
        raise RuntimeError(f"HTTP {e.code} on {method} {url}: {raw[:600]}") from e


def wait_lro(op_name: str, token: str, timeout_sec: int = 60) -> dict:
    url = f"https://dataplex.googleapis.com/v1/{op_name}"
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        _, data = rest_request("GET", url, token)
        if data.get("done"):
            if "error" in data:
                raise RuntimeError(f"LRO Error on {op_name}: {data['error']}")
            return data.get("response", data)
        time.sleep(1.5)
    raise TimeoutError(f"Timed out waiting for LRO {op_name}")


# ===========================================================================
# S04 & S06: GCS Bucket + ObjectRef IAM + Dataplex Knowledge Catalog
# ===========================================================================
def step_s04_s06_gcs_and_catalog(token: str) -> None:
    print("\n=== [S04/S06] GCS `gs://kmarket_okf` + ObjectRef IAM + Dataplex `ecommerce-okf` ===", flush=True)
    st_client = storage.Client(project=PROJECT)
    bucket = st_client.bucket(BUCKET)
    if not bucket.exists():
        bucket = st_client.create_bucket(BUCKET, location=LOCATION)
        print(f"[GCS] Created bucket gs://{BUCKET} in {LOCATION}", flush=True)
    else:
        print(f"[GCS] Bucket gs://{BUCKET} already exists", flush=True)

    # Grant ObjectRef Connection SA roles/storage.objectViewer on gs://kmarket_okf
    conn_url = f"https://bigqueryconnection.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}/connections/okf-gcs-conn"
    _, conn_info = rest_request("GET", conn_url, token)
    conn_sa = conn_info.get("cloudResource", {}).get("serviceAccountId")
    if conn_sa:
        policy = bucket.get_iam_policy(requested_policy_version=3)
        policy.bindings.append({
            "role": "roles/storage.objectViewer",
            "members": {f"serviceAccount:{conn_sa}"},
        })
        bucket.set_iam_policy(policy)
        print(f"[S06 IAM] Granted roles/storage.objectViewer on gs://{BUCKET} to {conn_sa}", flush=True)

    # Upload all files in ecommerce/okf (excluding verification.json)
    files_to_upload: list[tuple[str, str]] = []
    for root, _dirs, files in os.walk(OKF_DIR):
        for fname in sorted(files):
            if fname == "verification.json":
                continue
            abs_p = os.path.join(root, fname)
            rel_p = os.path.relpath(abs_p, OKF_DIR)
            files_to_upload.append((abs_p, f"{PREFIX}/{rel_p}"))

    def _upload_one(item: tuple[str, str]) -> str:
        abs_p, blob_name = item
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(abs_p, content_type="text/markdown; charset=utf-8" if abs_p.endswith(".md") else "text/yaml; charset=utf-8")
        return blob_name

    with ThreadPoolExecutor(max_workers=12) as ex:
        list(ex.map(_upload_one, files_to_upload))
    print(f"[GCS] Uploaded {len(files_to_upload)} objects to gs://{BUCKET}/{PREFIX}/", flush=True)

    # Create Dataplex EntryGroup `ecommerce-okf` if not exists
    parent = f"projects/{PROJECT}/locations/{LOCATION}"
    eg_name = f"{parent}/entryGroups/{ENTRY_GROUP}"
    eg_url = f"https://dataplex.googleapis.com/v1/{eg_name}"
    code, _ = rest_request("GET", eg_url, token, ignore_status=(404,))
    if code == 404:
        create_eg_url = f"https://dataplex.googleapis.com/v1/{parent}/entryGroups?entryGroupId={ENTRY_GROUP}"
        _, op = rest_request("POST", create_eg_url, token, {
            "displayName": "K-Market Ecommerce OKF v0.2 Knowledge Catalog",
            "description": "K마켙 이커머스 법령·심사지침·사내내규 OKF v0.2 번들 엔트리 그룹",
        })
        if "name" in op and "/operations/" in op["name"]:
            wait_lro(op["name"], token)
        print(f"[KC] Created EntryGroup `{ENTRY_GROUP}`", flush=True)
    else:
        print(f"[KC] EntryGroup `{ENTRY_GROUP}` ready", flush=True)

    # Push all .md files to Dataplex `ecommerce-okf`
    from tools.push_catalog import split_frontmatter, to_aspect, source_update_time, parse_contacts_aspect

    md_rel_paths: list[str] = []
    for root, _dirs, files in os.walk(OKF_DIR):
        for fname in sorted(files):
            if fname.endswith(".md"):
                md_rel_paths.append(os.path.relpath(os.path.join(root, fname), OKF_DIR))

    def _upsert_kc_entry(rel: str) -> str:
        abs_p = os.path.join(OKF_DIR, rel)
        with open(abs_p, "r", encoding="utf-8") as fh:
            text = fh.read()
        fm, body = split_frontmatter(text)
        eid = rel[:-3] if rel.endswith(".md") else rel
        entry_name = f"projects/{PROJECT}/locations/{LOCATION}/entryGroups/{ENTRY_GROUP}/entries/{eid}"
        entry_type_res = f"projects/{PROJECT}/locations/{LOCATION}/entryTypes/{ENTRY_TYPE}"

        title = str(fm.get("title") or os.path.basename(rel))
        desc = str(fm.get("description") or f"K마켙 OKF bundle document {rel}")[:1000]
        aspect_data = to_aspect(fm)

        aspects_payload = {
            OKF_ASPECT: {
                "aspectType": f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/aspectTypes/okf",
                "data": aspect_data,
            },
            OVERVIEW_ASPECT: {
                "aspectType": "projects/dataplex-types/locations/global/aspectTypes/overview",
                "data": {
                    "content": body.strip() or f"# {title}",
                },
            },
        }
        contacts_data = parse_contacts_aspect(fm.get("contacts"))
        if contacts_data:
            aspects_payload["dataplex-types.global.contacts"] = {
                "aspectType": "projects/dataplex-types/locations/global/aspectTypes/contacts",
                "data": contacts_data,
            }

        entry_body = {
            "name": entry_name,
            "entryType": entry_type_res,
            "entrySource": {
                "resource": f"gs://{BUCKET}/{PREFIX}/{rel}",
                "system": "Open Knowledge Format",
                "platform": "OKF",
                "displayName": title[:250],
                "description": desc,
                "updateTime": source_update_time(fm),
            },
            "aspects": aspects_payload,
        }

        create_url = (
            f"https://dataplex.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}"
            f"/entryGroups/{ENTRY_GROUP}/entries?entryId={urllib.parse.quote(eid, safe='')}"
        )
        c_code, _ = rest_request("POST", create_url, token, entry_body, ignore_status=(409,))
        if c_code == 409:
            patch_url = (
                f"https://dataplex.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}"
                f"/entryGroups/{ENTRY_GROUP}/entries/{urllib.parse.quote(eid, safe='/')}"
                f"?updateMask=aspects,entrySource"
            )
            rest_request("PATCH", patch_url, token, entry_body)
        return eid

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = [ex.submit(_upsert_kc_entry, r) for r in md_rel_paths]
        for fut in as_completed(futures):
            fut.result()
    print(f"[KC] Upserted {len(md_rel_paths)} entries into Dataplex EntryGroup `{ENTRY_GROUP}`", flush=True)

    # Also upload & register the 2 Q21_D5 governance fixture snapshots under versions/
    fixtures_spec = [
        {
            "eid": "versions/md_art_002_margin_guardrail_v0.1.0",
            "title": "제2조(실현마진율 산정 산식 및 구버전 15% 가드레일 — 폐기 스냅샷 v0.1.0)",
            "fm": {
                "type": "Provision",
                "version": "0.1.0",
                "status": "deprecated",
                "superseded_by": "",
                "content_class": "internal_policy",
                "treatment": "verbatim_ko",
                "source_pdf": "08_INTERNAL_K마켙_MD상품마진_및_체화재고_가격결정_내규_2025.pdf",
                "source_page": 1,
                "section_number": "제1조~제2조",
                "title": "제2조(실현마진율 산정 산식 및 구버전 15% 가드레일 — 폐기 스냅샷 v0.1.0)",
                "updated_at": "2024-12-31",
            },
            "body": (
                "# 제2조(실현마진율 산정 산식 및 구버전 15% 가드레일 — 폐기 스냅샷 v0.1.0)\n\n"
                "① [폐기된 구버전 조문] 개별 주문품목의 프로모션 최저마진 가드레일은 15.0% 이상으로 한다. "
                "(2025년 개정으로 폐기 — 현행 상시 가드레일 25.0% 조문 참조)\n"
            ),
        },
        {
            "eid": "versions/md_art_002_margin_guardrail_v0_1_0",
            "title": "제2조(구버전 마진 가드레일 v0_1_0 ➔ 현행 25% 가드레일 대체 체인)",
            "fm": {
                "type": "Provision",
                "version": "0.1.0",
                "status": "deprecated",
                "superseded_by": "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail",
                "content_class": "internal_policy",
                "treatment": "verbatim_ko",
                "source_pdf": "08_INTERNAL_K마켙_MD상품마진_및_체화재고_가격결정_내규_2025.pdf",
                "source_page": 1,
                "section_number": "제1조~제2조",
                "title": "제2조(구버전 마진 가드레일 v0_1_0 ➔ 현행 25% 가드레일 대체 체인)",
                "updated_at": "2025-01-01",
            },
            "body": (
                "# 제2조(구버전 마진 가드레일 v0_1_0 — 현행 조문으로 대체됨)\n\n"
                "본 스냅샷은 `internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail` (상시 25.0% 가드레일)으로 대체(superseded)되었습니다.\n"
            ),
        },
    ]
    for fx in fixtures_spec:
        eid = fx["eid"]
        rel_md = f"{eid}.md"
        full_md = "---\n" + yaml.safe_dump(fx["fm"], allow_unicode=True, sort_keys=False) + "---\n\n" + fx["body"]
        blob = bucket.blob(f"{PREFIX}/{rel_md}")
        blob.upload_from_string(full_md.encode("utf-8"), content_type="text/markdown; charset=utf-8")
        entry_name = f"projects/{PROJECT}/locations/{LOCATION}/entryGroups/{ENTRY_GROUP}/entries/{eid}"
        entry_type_res = f"projects/{PROJECT}/locations/{LOCATION}/entryTypes/{ENTRY_TYPE}"
        aspect_data = to_aspect(fx["fm"])
        entry_body = {
            "name": entry_name,
            "entryType": entry_type_res,
            "entrySource": {
                "resource": f"gs://{BUCKET}/{PREFIX}/{rel_md}",
                "system": "Open Knowledge Format",
                "platform": "OKF",
                "displayName": fx["title"][:250],
                "description": fx["title"],
                "updateTime": source_update_time(fx["fm"]),
            },
            "aspects": {
                OKF_ASPECT: {
                    "aspectType": f"projects/{PROJECT_NUMBER}/locations/{LOCATION}/aspectTypes/okf",
                    "data": aspect_data,
                },
                OVERVIEW_ASPECT: {
                    "aspectType": "projects/dataplex-types/locations/global/aspectTypes/overview",
                    "data": {"content": fx["body"]},
                },
            },
        }
        create_url = (
            f"https://dataplex.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}"
            f"/entryGroups/{ENTRY_GROUP}/entries?entryId={urllib.parse.quote(eid, safe='')}"
        )
        c_code, _ = rest_request("POST", create_url, token, entry_body, ignore_status=(409,))
        if c_code == 409:
            patch_url = (
                f"https://dataplex.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}"
                f"/entryGroups/{ENTRY_GROUP}/entries/{urllib.parse.quote(eid, safe='/')}"
                f"?updateMask=aspects,entrySource"
            )
            rest_request("PATCH", patch_url, token, entry_body)
    print(f"[KC] Upserted {len(fixtures_spec)} governance fixture entries (versions/*) into `{ENTRY_GROUP}`", flush=True)


# ===========================================================================
# S05: Spanner `kmarket_ecommerce` + BigQuery `kmarket_ecommerce` + Federation
# ===========================================================================
STR, INT, FLT, DATE, BOOL = "STRING", "INT64", "FLOAT64", "DATE", "BOOL"

SPANNER_TABLES: dict[str, dict[str, str]] = {
    "orders": {
        "order_id": STR, "user_id": STR, "status": STR,
        "num_of_item": INT, "created_at": STR, "shipped_at": STR,
        "delivered_at": STR, "returned_at": STR,
    },
    "order_items": {
        "item_id": STR, "order_id": STR, "user_id": STR,
        "product_id": STR, "inventory_item_id": STR, "status": STR,
        "retail_price_krw": INT, "sale_price_krw": INT,
        "coupon_discount_krw": INT, "coupon_type": STR,
        "return_reason_cd": STR, "created_at": STR,
        "shipped_at": STR, "delivered_at": STR, "returned_at": STR,
    },
    "inventory_items": {
        "inventory_item_id": STR, "product_id": STR,
        "distribution_center_id": STR, "inbound_date": STR,
        "age_days": INT, "avail_qty": INT, "stock_status": STR,
    },
    "events": {
        "event_id": STR, "user_id": STR, "session_id": STR,
        "sequence_number": INT, "event_type": STR, "product_id": STR,
        "traffic_source": STR, "created_at": STR,
    },
    "campaign_exceptions": {
        "approval_id": STR, "target_kind": STR, "product_id": STR,
        "item_id": STR, "approved_floor_margin_pct": FLT,
        "hologram_tag_intact_yn": STR, "vendor_voluntary_req_yn": STR,
        "approver_dept": STR, "approved_date": DATE, "status": STR,
    },
}

BQ_TABLES: dict[str, dict[str, str]] = {
    "users": {
        "user_id": STR, "user_name": STR, "age": INT, "gender": STR,
        "membership_tier": STR, "city": STR, "traffic_source": STR,
        "marketing_opt_in_yn": STR, "preferred_style": STR, "created_at": DATE,
    },
    "products": {
        "product_id": STR, "sku": STR, "product_name": STR,
        "brand_id": STR, "brand_name": STR, "department": STR,
        "category": STR, "style_tag": STR, "cost_krw": INT,
        "retail_price_krw": INT, "coord_product_id": STR,
        "substitute_product_id": STR, "return_policy_tag": STR,
        "distribution_center_id": STR,
    },
    "brand_vendor_contracts": {
        "brand_id": STR, "brand_name": STR, "trade_type": STR,
        "base_commission_pct": FLT, "agreed_promo_share_pct": FLT,
        "written_promo_agreement_yn": STR, "sla_ship_hours": INT,
    },
}


def coerce_val(val: str | None, kind: str) -> Any:
    if val is None or val == "":
        return None
    if kind == INT:
        return int(float(val))
    if kind == FLT:
        return float(val)
    if kind == DATE:
        return _dt.date.fromisoformat(val)
    if kind == BOOL:
        return val.lower() in ("true", "y", "1")
    return val


def step_s05_spanner_and_bigquery() -> None:
    print("\n=== [S05] Spanner `finance-cs/kmarket_ecommerce` + BigQuery `kmarket_ecommerce` + Federation ===", flush=True)
    sp_client = spanner.Client(project=PROJECT)
    instance = sp_client.instance(SPANNER_INSTANCE)
    db = instance.database(SPANNER_DATABASE)

    if db.exists():
        print(f"[Spanner] Dropping existing database {SPANNER_INSTANCE}/{SPANNER_DATABASE} to apply updated DDL...", flush=True)
        db.drop()

    with open(SPANNER_DDL_PATH, "r", encoding="utf-8") as fh:
        raw_ddl = fh.read()
    # Strip SQL comments and split by semicolon
    clean_ddl = re.sub(r"--[^\n]*", "", raw_ddl)
    ddl_stmts = [s.strip() for s in clean_ddl.split(";") if s.strip()]
    db = instance.database(SPANNER_DATABASE, ddl_statements=ddl_stmts)
    op = db.create()
    op.result(120)
    print(f"[Spanner] Created database {SPANNER_INSTANCE}/{SPANNER_DATABASE} with {len(ddl_stmts)} tables", flush=True)

    sp_total = 0
    for table, schema in SPANNER_TABLES.items():
        with open(os.path.join(CSV_DIR, f"{table}.csv"), "r", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        cols = list(schema.keys())
        vals = [[coerce_val(r.get(c), schema[c]) for c in cols] for r in rows]
        with db.batch() as batch:
            batch.delete(table, spanner.KeySet(all_=True))
        with db.batch() as batch:
            batch.insert(table=table, columns=cols, values=vals)
        sp_total += len(vals)
        print(f"  [Spanner] {table:<22}: {len(vals):>3} rows loaded", flush=True)
    print(f"[Spanner] Total loaded: {sp_total} rows", flush=True)

    bq_client = bigquery.Client(project=PROJECT, location=LOCATION)
    ds_id = f"{PROJECT}.{SRC_DS}"
    ds = bigquery.Dataset(ds_id)
    ds.location = LOCATION
    ds.description = "K마켙 (K-Market) 이커머스 마스터 3종 + Spanner 실시간 연합 뷰 5종"
    bq_client.create_dataset(ds, exists_ok=True)

    bq_total = 0
    for table, schema in BQ_TABLES.items():
        bq_schema = [bigquery.SchemaField(c, t) for c, t in schema.items()]
        job_cfg = bigquery.LoadJobConfig(
            schema=bq_schema,
            source_format=bigquery.SourceFormat.CSV,
            skip_leading_rows=1,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        with open(os.path.join(CSV_DIR, f"{table}.csv"), "rb") as fh:
            job = bq_client.load_table_from_file(fh, f"{ds_id}.{table}", job_config=job_cfg)
        job.result()
        n = bq_client.get_table(f"{ds_id}.{table}").num_rows
        bq_total += n
        print(f"  [BigQuery] {table:<22}: {n:>3} rows loaded", flush=True)
    print(f"[BigQuery] Total master rows loaded: {bq_total}", flush=True)

    # Create External Schema `kmarket_ecommerce_ext` + 5 `ont_*` views
    ext_source = f"google-cloudspanner:/projects/{PROJECT}/instances/{SPANNER_INSTANCE}/databases/{SPANNER_DATABASE}"
    ext_sql = (
        f"CREATE EXTERNAL SCHEMA IF NOT EXISTS `{PROJECT}.{EXT_DS}`\n"
        f"  OPTIONS (external_source = '{ext_source}', location = '{LOCATION}');"
    )
    bq_client.query(ext_sql).result()
    print(f"[Federation] Created external schema `{EXT_DS}` -> {SPANNER_INSTANCE}/{SPANNER_DATABASE}", flush=True)

    for tbl in SPANNER_TABLES:
        v_sql = (
            f"CREATE OR REPLACE VIEW `{PROJECT}.{SRC_DS}.ont_{tbl}` AS\n"
            f"SELECT * FROM `{PROJECT}.{EXT_DS}.{tbl}`;"
        )
        bq_client.query(v_sql).result()
        cnt = list(bq_client.query(f"SELECT COUNT(*) AS n FROM `{PROJECT}.{SRC_DS}.ont_{tbl}`").result())[0]["n"]
        print(f"  [Federation] {SRC_DS}.ont_{tbl:<22}: live count = {cnt}", flush=True)


# ===========================================================================
# S07: BigQuery `kmarket_ontology.ecommerce_graph` + Glossary + KC Aspect
# ===========================================================================
def load_table_rows(
    client: bigquery.Client,
    table_id: str,
    schema: list[bigquery.SchemaField],
    rows: list[dict],
    table_desc: str,
) -> None:
    full_id = f"{PROJECT}.{ONT_DS}.{table_id}"
    tbl = bigquery.Table(full_id, schema=schema)
    tbl.description = table_desc
    client.delete_table(full_id, not_found_ok=True)
    tbl = client.create_table(tbl)
    job_cfg = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")
    job = client.load_table_from_json(rows, full_id, job_config=job_cfg)
    job.result()
    print(f"  [BQ Ontology] {ONT_DS}.{table_id:<30}: {len(rows):>3} rows", flush=True)


def step_s07_ontology_graph_and_kc(token: str) -> None:
    print("\n=== [S07] BigQuery `kmarket_ontology.ecommerce_graph` + Glossary + KC Anchor Aspect ===", flush=True)
    bq_client = bigquery.Client(project=PROJECT, location=LOCATION)
    ont_ds_id = f"{PROJECT}.{ONT_DS}"
    ont_ds = bigquery.Dataset(ont_ds_id)
    ont_ds.location = LOCATION
    ont_ds.description = "K마켙 (K-Market) L1 이커머스 온톨로지 (LEX/CTX/Bridge + 11 Node Views + 15 Edge Views + ecommerce_graph)"
    bq_client.create_dataset(ont_ds, exists_ok=True)

    with open(VERIFICATION_JSON, "r", encoding="utf-8") as f:
        ver = json.load(f)
    with open(L1_YAML, "r", encoding="utf-8") as f:
        l1_cfg = yaml.safe_load(f)

    # 1. ctx_business_contexts (6 rows)
    ctx_schema = [
        bigquery.SchemaField("context_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("dept_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("purpose_summary", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("primary_metric_scope", "STRING", mode="NULLABLE"),
    ]
    ctx_rows = [
        {
            "context_id": "CRM_GROWTH",
            "dept_name": "그로스마케팅본부·AI추천랩",
            "purpose_summary": "장바구니 이탈 실시간 탐지, 개인정보 마케팅 동의 검증, 코디 번들·대체상품 추천 및 등급별 타겟팅 쿠폰 발급",
            "primary_metric_scope": "장바구니 미결제 세션(event_type='cart'), 마케팅 동의(marketing_opt_in=True), VVIP/VIP 최대 15% 번들 쿠폰",
        },
        {
            "context_id": "MD_MERCHANDISING",
            "dept_name": "MD본부·가격전략실",
            "purpose_summary": "상시 프로모션 최저 실현마진율(25%) 가드레일 통제 및 90일 이상 체화재고 클리어런스(10% 하한 완화) 승인",
            "primary_metric_scope": "실현마진율((sale_price_krw - cost_krw)/sale_price_krw >= 25%), 체화재고(stock_age_days >= 90) 10% 마진 완화",
        },
        {
            "context_id": "PARTNER_SETTLEMENT",
            "dept_name": "파트너상생본부·정산실",
            "purpose_summary": "입점브랜드 공동프로모션 사전 서면약정 확인 및 대규모유통업법 제11조 납품업자 판촉비 분담비율 50% 상한 캡 정산",
            "primary_metric_scope": "사전약정(signed_promo_agreement=True), 브랜드 분담률 캡 MIN(promo_cost_share_ratio, 0.50), 초과분 K마켙 흡수",
        },
        {
            "context_id": "CX_CS_SUPPORT",
            "dept_name": "고객경험(CX)본부·CS심사팀",
            "purpose_summary": "반품 사유별 청약철회 가능 기한(단순변심 7일 vs 표시·광고 상이 90일) 판정, 반품배송비 귀속 및 3영업일 환불 관리",
            "primary_metric_scope": "CHANGE_OF_MIND(7일/6,000원 고객부담), SIZE_MISMATCH_SPEC_DIFF(90일/무상반품), WEAR_AND_WASH_DAMAGE(청약철회 거절)",
        },
        {
            "context_id": "FULFILLMENT_OPS",
            "dept_name": "풀필먼트운영실",
            "purpose_summary": "김포·용인·양산 물류센터별 실시간 가용재고 관리 및 약속 출고 SLA(24h/36h/48h) 초과 시 지연보상 3,000P 지급",
            "primary_metric_scope": "가용재고(available_stock), 물류센터별 출고 SLA(김포 24h·용인 36h·양산 48h) 위반 감지 및 3,000P 자동 보상",
        },
        {
            "context_id": "LEGAL_COMPLIANCE",
            "dept_name": "준법감시실·개인정보보호팀",
            "purpose_summary": "대규모유통업법·전자상거래법·개보위 행태정보 가이드라인 준수 감리 및 자발적 판촉행사 신청·다크패턴 적격성 심사",
            "primary_metric_scope": "비동의 회원(marketing_opt_in=False) 타겟팅 차단, 상시 캠페인 자발성 예외 신청 기각(REJECTED), 해외직구 고시 혼동 방지",
        },
    ]
    load_table_rows(bq_client, "ctx_business_contexts", ctx_schema, ctx_rows, "[Node: BusinessContext] K마켙 본부·업무목적 맥락 (6건)")

    # 2. lex_source_documents (10 rows)
    doc_meta_map = {
        "DOC_01_LAW_LARGE_RETAIL": ("01", "binding", "DOMESTIC_ECOMMERCE", "공정거래위원회·법제처"),
        "DOC_02_FTC_PROMO_GUIDE": ("02", "binding", "DOMESTIC_ECOMMERCE", "공정거래위원회"),
        "DOC_03_LAW_ECOMMERCE": ("03", "binding", "DOMESTIC_ECOMMERCE", "공정거래위원회·법제처"),
        "DOC_04_FTC_DARK_PATTERN": ("04", "advisory", "DOMESTIC_ECOMMERCE", "공정거래위원회"),
        "DOC_05_PIPC_BEHAVIORAL": ("05", "advisory", "DOMESTIC_ECOMMERCE", "개인정보보호위원회"),
        "DOC_06_DISTRACTOR_CUSTOMS": ("06", "distractor", "OVERSEAS_DIRECT_CUSTOMS", "관세청"),
        "DOC_07_KMARKET_CRM_POLICY": ("07", "internal", "DOMESTIC_ECOMMERCE", "주식회사 K마켙 그로스마케팅본부"),
        "DOC_08_KMARKET_MD_POLICY": ("08", "internal", "DOMESTIC_ECOMMERCE", "주식회사 K마켙 MD본부"),
        "DOC_09_KMARKET_PARTNER_POLICY": ("09", "internal", "DOMESTIC_ECOMMERCE", "주식회사 K마켙 파트너상생본부"),
        "DOC_10_KMARKET_CS_SLA_POLICY": ("10", "internal", "DOMESTIC_ECOMMERCE", "주식회사 K마켙 고객경험본부"),
    }
    doc_schema = [
        bigquery.SchemaField("doc_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("doc_code", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("title", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("authority_level", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("applicable_sector", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("issuing_body", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("kc_entry_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("gcs_uri", "STRING", mode="NULLABLE"),
    ]
    doc_rows = []
    for d in ver["documents"]:
        did = d["doc_id"]
        code, auth, sector, issuer = doc_meta_map[did]
        cid = d["concept_id"]
        doc_rows.append({
            "doc_id": did,
            "doc_code": code,
            "title": d["title"],
            "authority_level": auth,
            "applicable_sector": sector,
            "issuing_body": issuer,
            "kc_entry_id": cid,
            "gcs_uri": f"gs://{BUCKET}/{PREFIX}/{cid}.md",
        })
    load_table_rows(bq_client, "lex_source_documents", doc_schema, doc_rows, "[Node: SourceDocument] K마켙 법령·심사지침·사내내규 원본 문서 루트 (10건)")

    # 3. lex_provisions (36 rows)
    prov_schema = [
        bigquery.SchemaField("provision_slot_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("doc_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("kc_entry_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("article_no", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("title", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("provision_role", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("target_columns", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("missing_schema_columns", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("gcs_uri", "STRING", mode="NULLABLE"),
    ]
    missing_cols_map = {
        "regulations/01_law_large_retail_fair_trade/ch02_payment_and_return_ban/art_008_payment_deadline":
            "orders.monthly_closing_date,orders.vendor_payout_paid_at",
        "regulations/02_ftc_promo_cost_guideline/sec02_cap_override_and_voluntary_test/guide_05_voluntary_differentiated_test":
            "campaign_exceptions.voluntary_request_doc_uri,campaign_exceptions.expected_uplift_roi_pct",
        "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_004_voluntary_filing_review":
            "campaign_exceptions.voluntary_request_doc_uri,campaign_exceptions.expected_uplift_roi_pct",
        "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p2_withdrawal_restrictions":
            "campaign_exceptions.inspection_photo_gcs_uri,order_items.seal_serial_no",
        "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch01_return_reason_and_shipping_fee/cs_art_001_002_return_reason_rules":
            "campaign_exceptions.inspection_photo_gcs_uri,order_items.seal_serial_no",
        "regulations/04_ftc_dark_pattern_and_reco_guideline/ch01_price_and_stock_truthfulness/dp_art_001_002_price_display":
            "products.min_sale_price_20d_krw,products.price_reference_verified_at",
        "regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_004_005_retention_and_night_ban":
            "users.night_push_opt_in_yn,events.push_scheduled_at",
        "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_004_005_tier_coupon_and_night_rule":
            "users.night_push_opt_in_yn,events.push_scheduled_at",
    }
    prov_rows = []
    for p in ver["provisions"]:
        cid = p["concept_id"]
        if p["category"] == "distractors":
            role = "DISTRACTOR_RULE"
            tcols = "ont_orders.order_id,ont_inventory_items.distribution_center"
        elif p["category"] == "internal_policies":
            if "art_003" in cid or "art_004" in cid:
                role = "EXCEPTION_PROVISO"
            else:
                role = "INTERNAL_RULE"
            tcols = "users.marketing_opt_in,products.cost_krw,ont_inventory_items.available_stock,ont_order_items.coupon_discount_krw,brand_vendor_contracts.promo_cost_share_ratio"
        else:
            if "p3_p5" in cid or "voluntary" in cid or "p2_withdrawal" in cid:
                role = "EXCEPTION_PROVISO"
            else:
                role = "BASE_CRITERIA"
            tcols = "ont_order_items.coupon_discount_krw,brand_vendor_contracts.promo_cost_share_ratio,ont_orders.delivered_at,ont_orders.return_requested_at"

        prov_rows.append({
            "provision_slot_id": cid,
            "doc_id": p["doc_id"],
            "kc_entry_id": cid,
            "article_no": p["section_number"],
            "title": p["title"],
            "provision_role": role,
            "target_columns": tcols,
            "missing_schema_columns": missing_cols_map.get(cid, ""),
            "gcs_uri": f"gs://{BUCKET}/{PREFIX}/{cid}.md",
        })
    load_table_rows(bq_client, "lex_provisions", prov_schema, prov_rows, "[Node: Provision] K마켙 36개 조문·심사기준·사내내규 슬롯 노드")

    # 4. Bridge & LEX Edge tables
    inv_schema = [
        bigquery.SchemaField("edge_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("context_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("term_key", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("glossary_term_uri", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("provision_slot_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("invocation_reason", "STRING", mode="NULLABLE"),
    ]
    g_base = f"projects/{PROJECT}/locations/{LOCATION}/glossaries/{GLOSSARY_ID}/terms"
    inv_rows = [
        {"edge_id": "INV_CRM_01", "context_id": "CRM_GROWTH", "term_key": "hyper-personalized-reco", "glossary_term_uri": f"{g_base}/hyper-personalized-reco", "provision_slot_id": "internal_policies/07_kmarket_crm_hyper_personalization/ch01_cart_abandon_and_optin_gate/crm_art_001_002_cart_abandon_optin", "invocation_reason": "장바구니 이탈 실시간 탐지 및 marketing_opt_in=True 필수 검증"},
        {"edge_id": "INV_CRM_02", "context_id": "CRM_GROWTH", "term_key": "hyper-personalized-reco", "glossary_term_uri": f"{g_base}/hyper-personalized-reco", "provision_slot_id": "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle", "invocation_reason": "품절 시 대체상품 전환 및 정상재고 시 코디 번들 크로스셀 추천"},
        {"edge_id": "INV_CRM_03", "context_id": "CRM_GROWTH", "term_key": "hyper-personalized-reco", "glossary_term_uri": f"{g_base}/hyper-personalized-reco", "provision_slot_id": "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_004_005_tier_coupon_and_night_rule", "invocation_reason": "회원 등급별 최대 쿠폰 할인율(VVIP/VIP 15%) 및 25% 마진 가드레일 연동"},
        {"edge_id": "INV_MD_01", "context_id": "MD_MERCHANDISING", "term_key": "margin-guardrail", "glossary_term_uri": f"{g_base}/margin-guardrail", "provision_slot_id": "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail", "invocation_reason": "실현마진율 산식 및 상시 프로모션 25.0% 최저마진 가드레일 검증"},
        {"edge_id": "INV_MD_02", "context_id": "MD_MERCHANDISING", "term_key": "clearance-exception", "glossary_term_uri": f"{g_base}/clearance-exception", "provision_slot_id": "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_003_aged_inventory_10pct_floor", "invocation_reason": "입고 90일 이상 체화재고 최저마진 10.0% 완화 및 최대 30% 클리어런스 특례"},
        {"edge_id": "INV_MD_03", "context_id": "MD_MERCHANDISING", "term_key": "clearance-exception", "glossary_term_uri": f"{g_base}/clearance-exception", "provision_slot_id": "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_004_campaign_exception_override", "invocation_reason": "캠페인 예외승인 원장(campaign_exceptions) APPROVED 확인 및 마진 완화 적용"},
        {"edge_id": "INV_PRT_01", "context_id": "PARTNER_SETTLEMENT", "term_key": "promo-cost-sharing", "glossary_term_uri": f"{g_base}/promo-cost-sharing", "provision_slot_id": "regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p3_p5_fifty_percent_cap_and_proviso", "invocation_reason": "대규모유통업법 제11조제4항 납품업자 판촉비 분담비율 50% 상한 강행규정"},
        {"edge_id": "INV_PRT_02", "context_id": "PARTNER_SETTLEMENT", "term_key": "promo-cost-sharing", "glossary_term_uri": f"{g_base}/promo-cost-sharing", "provision_slot_id": "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula", "invocation_reason": "쿠폰 분담금 50% 상한 캡(MIN(promo_cost_share_ratio, 0.50)) 및 초과분 K마켙 흡수 산식"},
        {"edge_id": "INV_PRT_03", "context_id": "PARTNER_SETTLEMENT", "term_key": "promo-cost-sharing", "glossary_term_uri": f"{g_base}/promo-cost-sharing", "provision_slot_id": "internal_policies/09_kmarket_vendor_promo_settlement/ch01_prior_agreement_verification/partner_art_001_002_prior_agreement", "invocation_reason": "공동판촉 사전 서면약정(signed_promo_agreement=True) 검증 및 미약정 시 K마켙 100% 부담"},
        {"edge_id": "INV_PRT_04", "context_id": "PARTNER_SETTLEMENT", "term_key": "promo-cost-sharing", "glossary_term_uri": f"{g_base}/promo-cost-sharing", "provision_slot_id": "regulations/01_law_large_retail_fair_trade/ch02_payment_and_return_ban/art_008_payment_deadline", "invocation_reason": "대규모유통업법 제8조 직매입 60일·특약매입/위수탁 40일 납품대금 지급기한 및 지연이자 연 15.5%"},
        {"edge_id": "INV_LGL_01", "context_id": "LEGAL_COMPLIANCE", "term_key": "behavioral-privacy-optin", "glossary_term_uri": f"{g_base}/behavioral-privacy-optin", "provision_slot_id": "regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_003_optin_requirement", "invocation_reason": "개보위 행태정보 가이드라인 제3조 회원 식별 결합 타겟팅 시 marketing_opt_in=True 필수"},
        {"edge_id": "INV_LGL_02", "context_id": "LEGAL_COMPLIANCE", "term_key": "promo-cost-sharing", "glossary_term_uri": f"{g_base}/promo-cost-sharing", "provision_slot_id": "regulations/02_ftc_promo_cost_guideline/sec02_cap_override_and_voluntary_test/guide_05_voluntary_differentiated_test", "invocation_reason": "공정위 심사지침 Ⅱ.5 법 제11조제5항 단서(자발성·차별성) 엄격 심사 및 상시 캠페인 예외 기각"},
        {"edge_id": "INV_LGL_03", "context_id": "LEGAL_COMPLIANCE", "term_key": "hyper-personalized-reco", "glossary_term_uri": f"{g_base}/hyper-personalized-reco", "provision_slot_id": "regulations/04_ftc_dark_pattern_and_reco_guideline/ch01_price_and_stock_truthfulness/dp_art_003_stock_truthfulness", "invocation_reason": "공정위 다크패턴 가이드라인 제3조 실시간 가용재고 연동 품절 표시 및 대체상품 객관적 안내"},
        {"edge_id": "INV_CX_01", "context_id": "CX_CS_SUPPORT", "term_key": "return-withdrawal-eligibility", "glossary_term_uri": f"{g_base}/return-withdrawal-eligibility", "provision_slot_id": "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods", "invocation_reason": "전자상거래법 제17조제1항 단순변심 7일 vs 표시·광고 상이 3개월(90일) 청약철회 기한"},
        {"edge_id": "INV_CX_02", "context_id": "CX_CS_SUPPORT", "term_key": "return-withdrawal-eligibility", "glossary_term_uri": f"{g_base}/return-withdrawal-eligibility", "provision_slot_id": "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch01_return_reason_and_shipping_fee/cs_art_001_002_return_reason_rules", "invocation_reason": "반품 사유 코드별 청약철회 적격성 및 왕복배송비(6,000원) 부담 주체 판정"},
        {"edge_id": "INV_CX_03", "context_id": "CX_CS_SUPPORT", "term_key": "return-withdrawal-eligibility", "glossary_term_uri": f"{g_base}/return-withdrawal-eligibility", "provision_slot_id": "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_003_refund_3days_and_no_customs", "invocation_reason": "회수 후 3영업일 이내 대금 환급(초과 시 지연배상금 연 15%) 및 해외직구 통관고시 적용 금지"},
        {"edge_id": "INV_OPS_01", "context_id": "FULFILLMENT_OPS", "term_key": "fulfillment-sla-compensation", "glossary_term_uri": f"{g_base}/fulfillment-sla-compensation", "provision_slot_id": "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_004_fulfillment_sla_compensation", "invocation_reason": "물류센터별 출고 SLA(24h/36h/48h) 위반 시 지연보상 3,000P 자동 지급"},
    ]
    load_table_rows(bq_client, "edge_invokes_provision", inv_schema, inv_rows, "[Edge: INVOKES_PROVISION] 본부 맥락 및 용어별 호출 조문 매핑")

    exc_schema = [
        bigquery.SchemaField("edge_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("base_slot_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("proviso_slot_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("exception_condition", "STRING", mode="NULLABLE"),
    ]
    exc_rows = [
        {
            "edge_id": "PROVISO_MARGIN_CLEARANCE",
            "base_slot_id": "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail",
            "proviso_slot_id": "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_003_aged_inventory_10pct_floor",
            "exception_condition": "입고 후 90일 이상 경과(stock_age_days >= 90) 및 가용재고 30개 이상 체화재고는 최저마진 하한을 25%에서 10%로 완화",
        },
        {
            "edge_id": "PROVISO_MARGIN_CAMPAIGN_EXC",
            "base_slot_id": "internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail",
            "proviso_slot_id": "internal_policies/08_kmarket_md_margin_and_clearance/ch02_aged_inventory_clearance_and_exceptions/md_art_004_campaign_exception_override",
            "exception_condition": "캠페인 예외승인 원장(campaign_exceptions)에 CLEARANCE_OVERRIDE 또는 VIP_RETENTION이 APPROVED된 경우 승인된 마진 하한 적용",
        },
        {
            "edge_id": "PROVISO_PROMO_VOLUNTARY",
            "base_slot_id": "regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p3_p5_fifty_percent_cap_and_proviso",
            "proviso_slot_id": "regulations/02_ftc_promo_cost_guideline/sec02_cap_override_and_voluntary_test/guide_05_voluntary_differentiated_test",
            "exception_condition": "납품업자의 자발적 요청(자발성)과 타 브랜드 대비 차별성이 모두 입증된 단독 행사에 한하여 50% 상한 예외 허용(상시 캠페인 배제)",
        },
        {
            "edge_id": "PROVISO_PARTNER_VOLUNTARY",
            "base_slot_id": "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula",
            "proviso_slot_id": "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_004_voluntary_filing_review",
            "exception_condition": "입점사 자발적·차별화 단독 행사 승인(VENDOR_VOLUNTARY_PROMO, ACTIVE) 시 약정 분담률 허용, 상시 캠페인은 기각(REJECTED)",
        },
        {
            "edge_id": "PROVISO_WITHDRAWAL_RESTRICTION",
            "base_slot_id": "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods",
            "proviso_slot_id": "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p2_withdrawal_restrictions",
            "exception_condition": "수령 후 7일 이내라도 소비자 귀책으로 세탁·수선·착용 흔적이 발생하여 가치가 현저히 감소한 경우 청약철회 제한",
        },
    ]
    load_table_rows(bq_client, "edge_has_exception_proviso", exc_schema, exc_rows, "[Edge: HAS_EXCEPTION_PROVISO] 본칙→단서/특례 조문 분기")

    del_schema = [
        bigquery.SchemaField("edge_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("external_slot_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("internal_slot_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("delegation_scope", "STRING", mode="NULLABLE"),
    ]
    del_rows = [
        {
            "edge_id": "DEL_LAW11_TO_PARTNER03",
            "external_slot_id": "regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p3_p5_fifty_percent_cap_and_proviso",
            "internal_slot_id": "internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula",
            "delegation_scope": "대규모유통업법 제11조제4항 50% 상한 규정을 K마켙 정산 시스템 산식 MIN(promo_cost_share_ratio, 0.50)으로 구체화",
        },
        {
            "edge_id": "DEL_PIPC03_TO_CRM02",
            "external_slot_id": "regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_003_optin_requirement",
            "internal_slot_id": "internal_policies/07_kmarket_crm_hyper_personalization/ch01_cart_abandon_and_optin_gate/crm_art_001_002_cart_abandon_optin",
            "delegation_scope": "개보위 행태정보 가이드라인 제3조 식별 결합 동의 요건을 K마켙 장바구니 리마인드 users.marketing_opt_in=True 게이트로 구체화",
        },
        {
            "edge_id": "DEL_ECOM17_TO_CS02",
            "external_slot_id": "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods",
            "internal_slot_id": "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch01_return_reason_and_shipping_fee/cs_art_001_002_return_reason_rules",
            "delegation_scope": "전자상거래법 제17조 청약철회 기한을 K마켙 반품사유 코드(CHANGE_OF_MIND 7일 vs SIZE_MISMATCH_SPEC_DIFF 90일)로 구체화",
        },
        {
            "edge_id": "DEL_DP03_TO_CRM03",
            "external_slot_id": "regulations/04_ftc_dark_pattern_and_reco_guideline/ch01_price_and_stock_truthfulness/dp_art_003_stock_truthfulness",
            "internal_slot_id": "internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle",
            "delegation_scope": "공정위 다크패턴 가이드라인 제3조 실시간 재고·대체상품 안내 원칙을 K마켙 내규 제3조 품절 대체·코디 번들 추천 규칙으로 구체화",
        },
        {
            "edge_id": "DEL_ECOM18_TO_CS03",
            "external_slot_id": "regulations/03_law_ecommerce_consumer_protection/ch03_refund_sla_and_dark_patterns/ecom_art_018_refund_and_return_shipping",
            "internal_slot_id": "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_003_refund_3days_and_no_customs",
            "delegation_scope": "전자상거래법 제18조 3영업일 환급 및 지연배상금 연 15% 규정을 K마켙 CS 내규 제3조로 구체화",
        },
    ]
    load_table_rows(bq_client, "edge_delegates_to_internal", del_schema, del_rows, "[Edge: DELEGATES_TO_INTERNAL] 상위 법령→K마켙 사내내규 위임")

    conf_schema = [
        bigquery.SchemaField("edge_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("ecommerce_slot_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("distractor_slot_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("conflict_warning", "STRING", mode="NULLABLE"),
    ]
    conf_rows = [
        {
            "edge_id": "CONF_DOMESTIC_VS_CUSTOMS_01",
            "ecommerce_slot_id": "regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods",
            "distractor_slot_id": "distractors/06_distractor_customs_overseas_direct/ch01_overseas_customs_scope/dist_customs_art_003_return_fee",
            "conflict_warning": "국내 풀필먼트(김포·용인·양산) 출고 주문에는 전자상거래법 제17조(7일/90일, 반품배송비 6,000원)가 적용되며, 관세청 해외직구 특송고시(14일·국제반송수수료 35,000원)를 혼동 적용하면 안 됨",
        },
        {
            "edge_id": "CONF_CS_POLICY_VS_CUSTOMS_02",
            "ecommerce_slot_id": "internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_003_refund_3days_and_no_customs",
            "distractor_slot_id": "distractors/06_distractor_customs_overseas_direct/ch01_overseas_customs_scope/dist_customs_art_001_002_scope",
            "conflict_warning": "K마켙 국내 물류센터 직매입·특약매입 출고 건에 해외직구 목록통관(미화 150달러) 및 국제반송 규정을 적용 금지",
        },
    ]
    load_table_rows(bq_client, "edge_conflicts_by_sector", conf_schema, conf_rows, "[Edge: CONFLICTS_BY_SECTOR] 국내 이커머스 규정 vs 해외직구 통관고시 대조군 분리")

    # 5. ont_entity_aliases (dynamically built from all 8 CSVs + l1.yaml glossary_terms & business_contexts)
    alias_schema = [
        bigquery.SchemaField("alias_text", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("canonical_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("entity_class", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("alias_group", "STRING", mode="REQUIRED"),
    ]
    alias_rows: list[dict[str, str]] = []
    seen_alias: set[str] = set()

    def _add_alias(surface: str, cid: str, ecls: str, agrp: str) -> None:
        s = (surface or "").strip()
        if not s or len(s) < 2 or s in seen_alias:
            return
        seen_alias.add(s)
        alias_rows.append({
            "alias_text": s,
            "canonical_id": cid,
            "entity_class": ecls,
            "alias_group": agrp,
        })

    # 5a. Users (60 rows)
    with open(os.path.join(CSV_DIR, "users.csv"), "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            _add_alias(row["user_id"], row["user_id"], "Customer", "USER_NAME_OR_ID")
            _add_alias(row["user_name"], row["user_id"], "Customer", "USER_NAME_OR_ID")

    # 5b. Brands (8 rows)
    with open(os.path.join(CSV_DIR, "brand_vendor_contracts.csv"), "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            _add_alias(row["brand_id"], row["brand_id"], "BrandVendorContract", "BRAND_NAME_OR_ID")
            _add_alias(row["brand_name"], row["brand_id"], "BrandVendorContract", "BRAND_NAME_OR_ID")

    # 5c. Products (30 rows + natural short names)
    with open(os.path.join(CSV_DIR, "products.csv"), "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            _add_alias(row["product_id"], row["product_id"], "Product", "PRODUCT_NAME_OR_ID")
            _add_alias(row["sku"], row["product_id"], "Product", "PRODUCT_NAME_OR_ID")
            _add_alias(row["product_name"], row["product_id"], "Product", "PRODUCT_NAME_OR_ID")

    for short_name, pid in [
        ("발마칸 코트", "PRD-3001"),
        ("캐시미어 발마칸 코트", "PRD-3001"),
        ("터틀넥 니트", "PRD-3002"),
        ("메리노울 터틀넥 니트", "PRD-3002"),
        ("코디 니트", "PRD-3002"),
        ("셀비지 트러커 자켓", "PRD-3003"),
        ("스웻 후디", "PRD-3004"),
        ("실크 스카프", "PRD-3005"),
        ("인도어 스윔수트", "PRD-3006"),
        ("실크 브라렛", "PRD-3007"),
        ("실크 레이스 브라렛", "PRD-3007"),
        ("알파인 자켓", "PRD-3008"),
        ("린넨 와이드 팬츠", "PRD-3009"),
        ("메종드실크 에센셜 아이템", "PRD-3012"),
    ]:
        _add_alias(short_name, pid, "Product", "PRODUCT_NAME_OR_ID")

    # 5d. Orders (15 rows), OrderItems (21 rows), InventoryItems (32 rows), Events (11 rows), CampaignExceptions (7 rows)
    with open(os.path.join(CSV_DIR, "orders.csv"), "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            _add_alias(row["order_id"], row["order_id"], "Order", "ORDER_ID")

    with open(os.path.join(CSV_DIR, "order_items.csv"), "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            _add_alias(row["item_id"], row["item_id"], "OrderItem", "ORDER_ITEM_ID")

    with open(os.path.join(CSV_DIR, "inventory_items.csv"), "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            _add_alias(row["inventory_item_id"], row["inventory_item_id"], "InventoryItem", "INVENTORY_ID")

    with open(os.path.join(CSV_DIR, "events.csv"), "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            _add_alias(row["event_id"], row["event_id"], "UserBehaviorEvent", "EVENT_OR_SESSION_ID")
            # Map session_id to the cart/purchase event_id so session lookups bind cleanly
            if row["event_type"] in ("cart", "purchase"):
                _add_alias(row["session_id"], row["event_id"], "UserBehaviorEvent", "EVENT_OR_SESSION_ID")

    with open(os.path.join(CSV_DIR, "campaign_exceptions.csv"), "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            _add_alias(row["approval_id"], row["approval_id"], "CampaignException", "EXCEPTION_APPROVAL_ID")

    # 5e. BusinessContexts (6 contexts + department aliases)
    for bctx in l1_cfg.get("business_contexts", []):
        _add_alias(bctx["context_id"], bctx["context_id"], "BusinessContext", "BUSINESS_CONTEXT")
        _add_alias(bctx["dept_name"], bctx["context_id"], "BusinessContext", "BUSINESS_CONTEXT")
    for dept_alias, ctx_id in [
        ("그로스마케팅본부", "CRM_GROWTH"),
        ("그로스마케팅", "CRM_GROWTH"),
        ("AI추천랩", "CRM_GROWTH"),
        ("MD본부", "MD_MERCHANDISING"),
        ("가격전략실", "MD_MERCHANDISING"),
        ("파트너상생본부", "PARTNER_SETTLEMENT"),
        ("파트너정산실", "PARTNER_SETTLEMENT"),
        ("고객경험본부", "CX_CS_SUPPORT"),
        ("CS심사팀", "CX_CS_SUPPORT"),
        ("풀필먼트운영실", "FULFILLMENT_OPS"),
        ("준법감시실", "LEGAL_COMPLIANCE"),
    ]:
        _add_alias(dept_alias, ctx_id, "BusinessContext", "BUSINESS_CONTEXT")

    # 5f. GlossaryTerms (7 terms + synonyms from l1.yaml)
    for gterm in l1_cfg.get("glossary_terms", []):
        tk = gterm["term_key"]
        _add_alias(tk, tk, "GlossaryTerm", "GLOSSARY_TERM")
        _add_alias(gterm["display_name"], tk, "GlossaryTerm", "GLOSSARY_TERM")
        for syn in gterm.get("synonyms", []):
            _add_alias(syn, tk, "GlossaryTerm", "GLOSSARY_TERM")

    # Also deprecated version snapshots
    _add_alias("versions/md_art_002_margin_guardrail_v0.1.0", "versions/md_art_002_margin_guardrail_v0.1.0", "Provision", "PROVISION_SLOT")
    _add_alias("versions/md_art_002_margin_guardrail_v0_1_0", "versions/md_art_002_margin_guardrail_v0_1_0", "Provision", "PROVISION_SLOT")

    load_table_rows(bq_client, "ont_entity_aliases", alias_schema, alias_rows, "K마켙 자연어 엔티티 별칭 정규화 매핑 테이블")

    # 6. Build 11 Node Views + 15 Edge Views + Property Graph `kmarket_ontology.ecommerce_graph`
    graph_sql = f"""
-- ============================================================================
-- 1. 11 NODE VIEWS IN `{PROJECT}.{ONT_DS}`
-- ============================================================================

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_business_context` AS
SELECT context_id, dept_name, purpose_summary, primary_metric_scope
FROM `{PROJECT}.{ONT_DS}.ctx_business_contexts`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_source_document` AS
SELECT
  doc_id, doc_code, title, authority_level, applicable_sector, issuing_body, kc_entry_id, gcs_uri,
  OBJ.MAKE_REF(gcs_uri, 'us-central1.okf-gcs-conn') AS gcs_obj_ref
FROM `{PROJECT}.{ONT_DS}.lex_source_documents`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_provision` AS
SELECT
  provision_slot_id, doc_id, kc_entry_id, article_no, title,
  provision_role, target_columns, missing_schema_columns, gcs_uri,
  OBJ.MAKE_REF(gcs_uri, 'us-central1.okf-gcs-conn') AS gcs_obj_ref
FROM `{PROJECT}.{ONT_DS}.lex_provisions`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_order_item` AS
SELECT
  item_id AS order_item_id,
  item_id,
  order_id, user_id, product_id, inventory_item_id,
  status, retail_price_krw, coupon_discount_krw, sale_price_krw,
  coupon_type AS campaign_id,
  coupon_type,
  return_reason_cd AS return_reason_code,
  return_reason_cd,
  created_at, shipped_at, delivered_at, returned_at
FROM `{PROJECT}.{SRC_DS}.ont_order_items`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_order` AS
SELECT
  order_id, user_id, status, created_at, shipped_at,
  delivered_at,
  returned_at AS return_requested_at,
  returned_at,
  num_of_item
FROM `{PROJECT}.{SRC_DS}.ont_orders`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_customer` AS
SELECT
  user_id, user_name, age, gender, city, membership_tier,
  (marketing_opt_in_yn = 'Y') AS marketing_opt_in,
  marketing_opt_in_yn,
  preferred_style AS primary_category,
  preferred_style,
  traffic_source,
  CAST(created_at AS STRING) AS created_at
FROM `{PROJECT}.{SRC_DS}.users`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_product` AS
SELECT
  product_id,
  sku AS sku_code,
  sku,
  product_name, category, department, brand_id, brand_name,
  cost_krw, retail_price_krw,
  style_tag AS style_tags,
  style_tag,
  coord_product_id AS complementary_product_id,
  coord_product_id,
  substitute_product_id,
  return_policy_tag,
  distribution_center_id,
  TRUE AS is_active
FROM `{PROJECT}.{SRC_DS}.products`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_brand_vendor_contract` AS
SELECT
  brand_id, brand_name,
  trade_type AS contract_type,
  trade_type,
  ROUND(base_commission_pct / 100.0, 4) AS commission_rate,
  base_commission_pct,
  ROUND(agreed_promo_share_pct / 100.0, 4) AS promo_cost_share_ratio,
  agreed_promo_share_pct,
  (written_promo_agreement_yn = 'Y') AS signed_promo_agreement,
  written_promo_agreement_yn,
  0.25 AS min_margin_guardrail,
  6000 AS return_shipping_fee_krw,
  sla_ship_hours
FROM `{PROJECT}.{SRC_DS}.brand_vendor_contracts`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_inventory_item` AS
SELECT
  inventory_item_id, product_id,
  distribution_center_id AS distribution_center,
  distribution_center_id,
  avail_qty AS available_stock,
  avail_qty,
  age_days AS stock_age_days,
  age_days,
  inbound_date,
  stock_status
FROM `{PROJECT}.{SRC_DS}.ont_inventory_items`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_user_behavior_event` AS
SELECT
  event_id, user_id, session_id, sequence_number,
  product_id, event_type, traffic_source, created_at
FROM `{PROJECT}.{SRC_DS}.ont_events`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_node_campaign_exception` AS
SELECT
  approval_id AS exception_id,
  approval_id,
  target_kind AS exception_type,
  target_kind,
  product_id,
  item_id,
  ROUND(approved_floor_margin_pct / 100.0, 4) AS approved_margin_floor,
  approved_floor_margin_pct,
  hologram_tag_intact_yn,
  vendor_voluntary_req_yn,
  approver_dept AS approved_by_role,
  approver_dept,
  approved_date AS valid_until,
  approved_date,
  status
FROM `{PROJECT}.{SRC_DS}.ont_campaign_exceptions`;

-- ============================================================================
-- 2. 15 EDGE VIEWS IN `{PROJECT}.{ONT_DS}`
-- ============================================================================

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_scopes_portfolio` AS
SELECT
  CONCAT('SCOPE_', ctx.context_id, '_', oi.item_id) AS edge_id,
  ctx.context_id,
  oi.item_id AS order_item_id,
  CASE
    WHEN oi.status = 'Returned' OR oi.return_reason_cd != 'NONE' THEN 'CS_RETURN_AND_WITHDRAWAL_SCOPE'
    WHEN oi.coupon_discount_krw > 0 THEN 'PROMO_MARGIN_AND_VENDOR_SHARE_SCOPE'
    ELSE 'STANDARD_ORDER_FULFILLMENT_SCOPE'
  END AS portfolio_scope_rule
FROM `{PROJECT}.{ONT_DS}.ctx_business_contexts` ctx
CROSS JOIN `{PROJECT}.{SRC_DS}.ont_order_items` oi;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_belongs_to_order` AS
SELECT item_id AS order_item_id, order_id
FROM `{PROJECT}.{SRC_DS}.ont_order_items`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_placed_by_user` AS
SELECT order_id, user_id
FROM `{PROJECT}.{SRC_DS}.ont_orders`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_of_product` AS
SELECT item_id AS order_item_id, product_id
FROM `{PROJECT}.{SRC_DS}.ont_order_items`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_supplied_by_brand` AS
SELECT product_id, brand_id
FROM `{PROJECT}.{SRC_DS}.products`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_stocked_at_inventory` AS
SELECT product_id, inventory_item_id
FROM `{PROJECT}.{SRC_DS}.ont_inventory_items`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_logged_event_on_product` AS
SELECT event_id, product_id, user_id, event_type
FROM `{PROJECT}.{SRC_DS}.ont_events`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_has_campaign_exception` AS
SELECT
  product_id,
  approval_id AS exception_id,
  target_kind AS exception_type,
  status
FROM `{PROJECT}.{SRC_DS}.ont_campaign_exceptions`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_invokes_provision` AS
SELECT edge_id, context_id, term_key, glossary_term_uri, provision_slot_id, invocation_reason
FROM `{PROJECT}.{ONT_DS}.edge_invokes_provision`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_governed_by_criteria` AS
SELECT
  CONCAT('GOV_PROMO_', oi.item_id) AS edge_id,
  oi.item_id AS order_item_id,
  'regulations/01_law_large_retail_fair_trade/ch03_promo_cost_sharing_cap/art_011_p3_p5_fifty_percent_cap_and_proviso' AS provision_slot_id,
  '쿠폰할인 적용 주문품목 — 대규모유통업법 제11조제3항~제5항 납품업자 판촉비 50% 상한 심사 대상' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_order_items` oi
WHERE oi.coupon_discount_krw > 0
UNION ALL
SELECT
  CONCAT('GOV_SETTLE_', oi.item_id) AS edge_id,
  oi.item_id AS order_item_id,
  'internal_policies/09_kmarket_vendor_promo_settlement/ch02_fifty_percent_cap_settlement_formula/partner_art_003_cap_settlement_formula' AS provision_slot_id,
  '쿠폰할인 적용 주문품목 — K마켙 정산내규 제3조 브랜드 분담률 50% 캡 및 초과분 흡수 정산 대상' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_order_items` oi
WHERE oi.coupon_discount_krw > 0
UNION ALL
SELECT
  CONCAT('GOV_MARGIN_', oi.item_id) AS edge_id,
  oi.item_id AS order_item_id,
  'internal_policies/08_kmarket_md_margin_and_clearance/ch01_margin_formula_and_25pct_guardrail/md_art_001_002_margin_25pct_guardrail' AS provision_slot_id,
  '주문품목 실현마진율 산식 및 상시 25% 최저마진 가드레일 점검 대상' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_order_items` oi
UNION ALL
SELECT
  CONCAT('GOV_RET_LAW_', oi.item_id) AS edge_id,
  oi.item_id AS order_item_id,
  'regulations/03_law_ecommerce_consumer_protection/ch02_withdrawal_and_exceptions/ecom_art_017_p1_withdrawal_periods' AS provision_slot_id,
  '반품 신청 품목 — 전자상거래법 제17조 청약철회 가능 기한(7일 vs 90일) 심사 대상' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_order_items` oi
WHERE oi.status = 'Returned' OR oi.return_reason_cd != 'NONE'
UNION ALL
SELECT
  CONCAT('GOV_RET_CS_', oi.item_id) AS edge_id,
  oi.item_id AS order_item_id,
  'internal_policies/10_kmarket_cs_return_and_logistics_sla/ch01_return_reason_and_shipping_fee/cs_art_001_002_return_reason_rules' AS provision_slot_id,
  '반품 신청 품목 — K마켙 CS내규 제2조 반품사유 코드별 승인 여부 및 배송비(6,000원) 귀속 판정 대상' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_order_items` oi
WHERE oi.status = 'Returned' OR oi.return_reason_cd != 'NONE'
UNION ALL
SELECT
  CONCAT('GOV_SLA_', oi.item_id) AS edge_id,
  oi.item_id AS order_item_id,
  'internal_policies/10_kmarket_cs_return_and_logistics_sla/ch02_refund_3days_and_fulfillment_sla/cs_art_004_fulfillment_sla_compensation' AS provision_slot_id,
  '물류센터 출고 품목 — K마켙 내규 제4조 센터별 출고 SLA 준수 및 지연보상 판정 대상' AS binding_reason
FROM `{PROJECT}.{SRC_DS}.ont_order_items` oi;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_evaluated_under_provision` AS
SELECT
  CONCAT('EVAL_PIPC_', ev.event_id) AS edge_id,
  ev.event_id,
  'regulations/05_pipc_behavioral_targeting_guideline/ch02_optin_and_night_push_ban/pipc_art_003_optin_requirement' AS provision_slot_id,
  '고객 행동로그 기반 타겟팅 시 개보위 가이드라인 제3조 마케팅 수신동의(marketing_opt_in=True) 필수 검증' AS evaluation_reason
FROM `{PROJECT}.{SRC_DS}.ont_events` ev
WHERE ev.event_type = 'cart'
UNION ALL
SELECT
  CONCAT('EVAL_CRM02_', ev.event_id) AS edge_id,
  ev.event_id,
  'internal_policies/07_kmarket_crm_hyper_personalization/ch01_cart_abandon_and_optin_gate/crm_art_001_002_cart_abandon_optin' AS provision_slot_id,
  '장바구니 이탈 세션 탐지 및 마케팅 수신동의 검증 게이트' AS evaluation_reason
FROM `{PROJECT}.{SRC_DS}.ont_events` ev
WHERE ev.event_type = 'cart'
UNION ALL
SELECT
  CONCAT('EVAL_CRM03_', ev.event_id) AS edge_id,
  ev.event_id,
  'internal_policies/07_kmarket_crm_hyper_personalization/ch02_bundle_substitute_and_tier_coupon/crm_art_003_stock_substitute_bundle' AS provision_slot_id,
  '장바구니 상품 가용재고 연동 품절 대체상품 전환 및 코디 번들 크로스셀 추천 규칙' AS evaluation_reason
FROM `{PROJECT}.{SRC_DS}.ont_events` ev
WHERE ev.event_type = 'cart';

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_part_of_document` AS
SELECT provision_slot_id, doc_id
FROM `{PROJECT}.{ONT_DS}.lex_provisions`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_has_exception_proviso` AS
SELECT edge_id, base_slot_id, proviso_slot_id, exception_condition
FROM `{PROJECT}.{ONT_DS}.edge_has_exception_proviso`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_delegates_to_internal` AS
SELECT edge_id, external_slot_id, internal_slot_id, delegation_scope
FROM `{PROJECT}.{ONT_DS}.edge_delegates_to_internal`;

CREATE OR REPLACE VIEW `{PROJECT}.{ONT_DS}.v_edge_conflicts_by_sector` AS
SELECT edge_id, ecommerce_slot_id, distractor_slot_id, conflict_warning
FROM `{PROJECT}.{ONT_DS}.edge_conflicts_by_sector`;

-- ============================================================================
-- 3. CREATE OR REPLACE PROPERTY GRAPH `{PROJECT}.{ONT_DS}.{GRAPH_NAME}`
-- ============================================================================

CREATE OR REPLACE PROPERTY GRAPH `{PROJECT}.{ONT_DS}.{GRAPH_NAME}`
  NODE TABLES (
    `{PROJECT}.{ONT_DS}.v_node_business_context`
      KEY (context_id)
      LABEL BusinessContext,
    `{PROJECT}.{ONT_DS}.v_node_source_document`
      KEY (doc_id)
      LABEL SourceDocument,
    `{PROJECT}.{ONT_DS}.v_node_provision`
      KEY (provision_slot_id)
      LABEL Provision,
    `{PROJECT}.{ONT_DS}.v_node_order_item`
      KEY (order_item_id)
      LABEL OrderItem,
    `{PROJECT}.{ONT_DS}.v_node_order`
      KEY (order_id)
      LABEL `Order`,
    `{PROJECT}.{ONT_DS}.v_node_customer`
      KEY (user_id)
      LABEL Customer,
    `{PROJECT}.{ONT_DS}.v_node_product`
      KEY (product_id)
      LABEL Product,
    `{PROJECT}.{ONT_DS}.v_node_brand_vendor_contract`
      KEY (brand_id)
      LABEL BrandVendorContract,
    `{PROJECT}.{ONT_DS}.v_node_inventory_item`
      KEY (inventory_item_id)
      LABEL InventoryItem,
    `{PROJECT}.{ONT_DS}.v_node_user_behavior_event`
      KEY (event_id)
      LABEL UserBehaviorEvent,
    `{PROJECT}.{ONT_DS}.v_node_campaign_exception`
      KEY (exception_id)
      LABEL CampaignException
  )
  EDGE TABLES (
    `{PROJECT}.{ONT_DS}.v_edge_scopes_portfolio`
      KEY (edge_id)
      SOURCE KEY (context_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_business_context` (context_id)
      DESTINATION KEY (order_item_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_order_item` (order_item_id)
      LABEL SCOPES_PORTFOLIO,
    `{PROJECT}.{ONT_DS}.v_edge_belongs_to_order`
      KEY (order_item_id, order_id)
      SOURCE KEY (order_item_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_order_item` (order_item_id)
      DESTINATION KEY (order_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_order` (order_id)
      LABEL BELONGS_TO_ORDER,
    `{PROJECT}.{ONT_DS}.v_edge_placed_by_user`
      KEY (order_id, user_id)
      SOURCE KEY (order_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_order` (order_id)
      DESTINATION KEY (user_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_customer` (user_id)
      LABEL PLACED_BY_USER,
    `{PROJECT}.{ONT_DS}.v_edge_of_product`
      KEY (order_item_id, product_id)
      SOURCE KEY (order_item_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_order_item` (order_item_id)
      DESTINATION KEY (product_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_product` (product_id)
      LABEL OF_PRODUCT,
    `{PROJECT}.{ONT_DS}.v_edge_supplied_by_brand`
      KEY (product_id, brand_id)
      SOURCE KEY (product_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_product` (product_id)
      DESTINATION KEY (brand_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_brand_vendor_contract` (brand_id)
      LABEL SUPPLIED_BY_BRAND,
    `{PROJECT}.{ONT_DS}.v_edge_stocked_at_inventory`
      KEY (product_id, inventory_item_id)
      SOURCE KEY (product_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_product` (product_id)
      DESTINATION KEY (inventory_item_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_inventory_item` (inventory_item_id)
      LABEL STOCKED_AT_INVENTORY,
    `{PROJECT}.{ONT_DS}.v_edge_logged_event_on_product`
      KEY (event_id, product_id)
      SOURCE KEY (event_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_user_behavior_event` (event_id)
      DESTINATION KEY (product_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_product` (product_id)
      LABEL LOGGED_EVENT_ON_PRODUCT,
    `{PROJECT}.{ONT_DS}.v_edge_has_campaign_exception`
      KEY (product_id, exception_id)
      SOURCE KEY (product_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_product` (product_id)
      DESTINATION KEY (exception_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_campaign_exception` (exception_id)
      LABEL HAS_CAMPAIGN_EXCEPTION,
    `{PROJECT}.{ONT_DS}.v_edge_invokes_provision`
      KEY (edge_id)
      SOURCE KEY (context_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_business_context` (context_id)
      DESTINATION KEY (provision_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      LABEL INVOKES_PROVISION,
    `{PROJECT}.{ONT_DS}.v_edge_governed_by_criteria`
      KEY (edge_id)
      SOURCE KEY (order_item_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_order_item` (order_item_id)
      DESTINATION KEY (provision_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      LABEL GOVERNED_BY_CRITERIA,
    `{PROJECT}.{ONT_DS}.v_edge_evaluated_under_provision`
      KEY (edge_id)
      SOURCE KEY (event_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_user_behavior_event` (event_id)
      DESTINATION KEY (provision_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      LABEL EVALUATED_UNDER_PROVISION,
    `{PROJECT}.{ONT_DS}.v_edge_part_of_document`
      KEY (provision_slot_id, doc_id)
      SOURCE KEY (provision_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      DESTINATION KEY (doc_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_source_document` (doc_id)
      LABEL PART_OF_DOCUMENT,
    `{PROJECT}.{ONT_DS}.v_edge_has_exception_proviso`
      KEY (edge_id)
      SOURCE KEY (base_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      DESTINATION KEY (proviso_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      LABEL HAS_EXCEPTION_PROVISO,
    `{PROJECT}.{ONT_DS}.v_edge_delegates_to_internal`
      KEY (edge_id)
      SOURCE KEY (external_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      DESTINATION KEY (internal_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      LABEL DELEGATES_TO_INTERNAL,
    `{PROJECT}.{ONT_DS}.v_edge_conflicts_by_sector`
      KEY (edge_id)
      SOURCE KEY (ecommerce_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      DESTINATION KEY (distractor_slot_id) REFERENCES `{PROJECT}.{ONT_DS}.v_node_provision` (provision_slot_id)
      LABEL CONFLICTS_BY_SECTOR
  );
"""
    os.makedirs(os.path.dirname(GRAPH_SQL_PATH), exist_ok=True)
    with open(GRAPH_SQL_PATH, "w", encoding="utf-8") as fh:
        fh.write(graph_sql.strip() + "\n")
    bq_client.query(graph_sql).result()
    print(f"[BQ Graph] Deployed `{PROJECT}.{ONT_DS}.{GRAPH_NAME}` (11 Node Classes · 15 Edge Types)", flush=True)

    # 7. Dataplex Business Glossary `kmarket-ecommerce-glossary`
    parent = f"projects/{PROJECT}/locations/{LOCATION}"
    glossary_name = f"{parent}/glossaries/{GLOSSARY_ID}"
    glossary_url = f"https://dataplex.googleapis.com/v1/{glossary_name}"
    g_payload = {
        "displayName": "K마켙 이커머스 초개인화·마진·공정거래 표준 용어집",
        "description": "본부·업무목적 맥락(BusinessContext)에 따라 해석과 적용 조문(Provision)이 분기되는 K마켙 7대 핵심 이커머스 도메인 용어집",
        "labels": {"domain": "ecommerce-ontology", "company": "kmarket"},
    }
    code, _ = rest_request("GET", glossary_url, token, ignore_status=(404,))
    if code == 404:
        create_url = f"https://dataplex.googleapis.com/v1/{parent}/glossaries?glossaryId={GLOSSARY_ID}"
        _, op = rest_request("POST", create_url, token, g_payload)
        if "name" in op and "/operations/" in op["name"]:
            wait_lro(op["name"], token)
        print(f"[KC Glossary] Created `{GLOSSARY_ID}`", flush=True)
    else:
        patch_url = f"{glossary_url}?updateMask=displayName,description,labels"
        _, op = rest_request("PATCH", patch_url, token, g_payload)
        if "name" in op and "/operations/" in op["name"]:
            wait_lro(op["name"], token)
        print(f"[KC Glossary] Updated `{GLOSSARY_ID}`", flush=True)

    for term in l1_cfg.get("glossary_terms", []):
        tid = term["term_key"]
        term_name = f"{glossary_name}/terms/{tid}"
        term_url = f"https://dataplex.googleapis.com/v1/{term_name}"
        syns = ", ".join(term.get("synonyms", []))
        t_payload = {
            "displayName": term["display_name"],
            "description": f"{term['description']} [동의어·약칭: {syns}]",
            "parent": glossary_name,
            "labels": {"term_key": tid, "edge_binding": "invokes-provision"},
        }
        t_code, _ = rest_request("GET", term_url, token, ignore_status=(404,))
        if t_code == 404:
            create_t_url = f"https://dataplex.googleapis.com/v1/{glossary_name}/terms?termId={tid}"
            rest_request("POST", create_t_url, token, t_payload)
        else:
            patch_t_url = f"{term_url}?updateMask=displayName,description,labels"
            rest_request("PATCH", patch_t_url, token, t_payload)
    print(f"[KC Glossary] Synced {len(l1_cfg.get('glossary_terms', []))} terms in `{GLOSSARY_ID}`", flush=True)

    # 8. Attach `ontology-class-anchors` Aspect to `@bigquery` entries for `kmarket_ontology`
    class_anchors_list = []
    for nc in l1_cfg["node_classes"]:
        acfg = nc["kc_anchor_config"]
        props_str = " | ".join(
            f"{p['name']}({p['type']}): {p['description']}" for p in nc.get("properties", [])
        )
        class_anchors_list.append({
            "class_label": nc["class_label"],
            "layer": nc["layer"],
            "korean_name": nc["korean_name"],
            "description": nc["description"],
            "source_plane": nc["source_plane"],
            "graph_view": nc["graph_view"],
            "primary_key": nc["primary_key"],
            "anchor_type": acfg["anchor_type"],
            "alias_group": acfg["alias_group"],
            "match_bind_key": acfg["match_bind_key"],
            "gql_match_template": acfg["gql_match_template"],
            "planner_instruction": acfg["planner_instruction"],
            "outgoing_edges_csv": ", ".join(acfg.get("outgoing_edges", [])),
            "properties_summary": props_str,
        })

    aspect_key = f"{PROJECT_NUMBER}.{LOCATION}.{ANCHOR_ASPECT_ID}"
    aspect_type_name = f"{parent}/aspectTypes/{ANCHOR_ASPECT_ID}"
    aspect_data = {
        "graph_id": f"{PROJECT}.{ONT_DS}.{GRAPH_NAME}",
        "ontology_version": str(l1_cfg["meta"]["version"]),
        "alias_table_fqn": f"{PROJECT}.{ONT_DS}.ont_entity_aliases",
        "kc_glossary_resource": f"projects/{PROJECT}/locations/{LOCATION}/glossaries/{GLOSSARY_ID}",
        "governance_rule": (
            "Single Source of Governance: BigQuery Provision 노드는 불변 provision_slot_id와 kc_entry_id만 보유하며, "
            "문서 유효성(status∈{'stable','verified'} vs 'deprecated')과 대체 문서 체인(superseded_by)은 오직 Dataplex Knowledge Catalog의 "
            "ecommerce-okf okf Aspect에서만 실시간 검증합니다."
        ),
        "class_anchors": class_anchors_list,
        "edge_definitions_json": json.dumps(l1_cfg.get("edge_definitions", []), ensure_ascii=False),
        "glossary_terms_json": json.dumps(l1_cfg.get("glossary_terms", []), ensure_ascii=False),
    }

    target_entries = [
        f"projects/{PROJECT}/locations/{LOCATION}/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/{PROJECT}/datasets/{ONT_DS}/propertyGraphs/{GRAPH_NAME}",
        f"projects/{PROJECT}/locations/{LOCATION}/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/{PROJECT}/datasets/{ONT_DS}",
    ]
    for entry_path in target_entries:
        patch_entry_url = (
            f"https://dataplex.googleapis.com/v1/{entry_path}"
            f"?updateMask=aspects&aspectKeys={aspect_key}"
        )
        body = {
            "name": entry_path,
            "aspects": {
                aspect_key: {
                    "aspectType": aspect_type_name,
                    "data": aspect_data,
                }
            },
        }
        e_code, _ = rest_request("PATCH", patch_entry_url, token, body, ignore_status=(404,))
        if e_code == 404:
            print(f"  [KC Entry] Note: @bigquery entry not yet harvested for `{entry_path.split('/entries/')[-1]}` (will retry after harvest)", flush=True)
        else:
            print(f"  [KC Entry] Attached `{aspect_key}` to `{entry_path.split('/entries/')[-1]}`", flush=True)

    # 9. Verify Live GQL & ObjectRef on `kmarket_ontology.ecommerce_graph`
    print("\n=== [Verification] Live GQL + ObjectRef Test on `kmarket_ontology.ecommerce_graph` ===", flush=True)
    test_gql = f"""
    GRAPH `{PROJECT}.{ONT_DS}.{GRAPH_NAME}`
    MATCH (oi:OrderItem {{order_item_id: 'OIT-2026-0001'}})-[:OF_PRODUCT]->(p:Product)-[:SUPPLIED_BY_BRAND]->(b:BrandVendorContract),
          (oi)-[:GOVERNED_BY_CRITERIA]->(pr:Provision)
    RETURN
      oi.order_item_id AS order_item_id,
      p.product_name AS product_name,
      b.brand_name AS brand_name,
      oi.coupon_discount_krw AS coupon_discount_krw,
      b.promo_cost_share_ratio AS contract_ratio,
      LEAST(b.promo_cost_share_ratio, 0.50) AS legal_capped_ratio,
      CAST(oi.coupon_discount_krw * LEAST(b.promo_cost_share_ratio, 0.50) AS INT64) AS brand_share_krw,
      CAST(oi.coupon_discount_krw * (1.0 - LEAST(b.promo_cost_share_ratio, 0.50)) AS INT64) AS kmarket_share_krw,
      pr.article_no AS governing_article,
      OBJ.GET_ACCESS_URL(pr.gcs_obj_ref, 'r') AS signed_obj_url
    """
    gql_rows = [dict(r) for r in bq_client.query(test_gql).result()]
    print(f"[GQL Test] Returned {len(gql_rows)} rows for OIT-2026-0001:")
    for gr in gql_rows:
        u_obj = gr["signed_obj_url"]
        if isinstance(u_obj, str):
            u_obj = json.loads(u_obj)
        read_url = u_obj["access_urls"]["read_url"]
        http_code = urllib.request.urlopen(read_url, timeout=15).status
        print(
            f"  - {gr['order_item_id']} ({gr['product_name']} / {gr['brand_name']}): "
            f"coupon={gr['coupon_discount_krw']:,}원, contract_ratio={gr['contract_ratio']} -> "
            f"capped={gr['legal_capped_ratio']} (brand={gr['brand_share_krw']:,}원, K마켙={gr['kmarket_share_krw']:,}원) | "
            f"provision={gr['governing_article']} | ObjectRef GET={http_code}",
            flush=True,
        )


def main() -> None:
    sys.path.insert(0, ROOT)
    token = get_token()
    if "--only-s07" not in sys.argv:
        if "--skip-s04" not in sys.argv:
            step_s04_s06_gcs_and_catalog(token)
        step_s05_spanner_and_bigquery()
    step_s07_ontology_graph_and_kc(token)
    print("\n[ALL DONE] K마켙 (ecommerce-ontology) 3-Plane GCP deployment & live GQL/ObjectRef verification succeeded!", flush=True)


if __name__ == "__main__":
    main()
