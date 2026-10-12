"""BigQuery REST I/O for the Module 05 orchestrator (shared by studio_server and Agent Runtime).

Port of `tools/studio_server.py::run_bq_sql` / `resolve_bq_objectrefs_live` with identical
REST `jobs.query` response shape (string-typed cells) and identical masking, so the local UI and
the deployed Agent Runtime format ledger/provision values the same way. Only the credential source
differs: ADC (`google.auth.default`, retried) with a `gcloud` CLI fallback only where gcloud is
installed (workstations) — see `app/gcp_auth.py`.
"""

from __future__ import annotations

import concurrent.futures
import datetime as _dt
import json
import os
import time
import traceback
import urllib.request
from typing import Any

from app import gcp_auth

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "finance-ontology-changseop")
# On Agent Runtime PROJECT is the injected project number, so mask the ID separately (DR-07).
PROJECT_ID = os.environ.get("STARLIGHT_PROJECT_ID", "finance-ontology-changseop")
PROJECT_NUMBER = os.environ.get("STARLIGHT_PROJECT_NUMBER", "567090080191")
LOCATION = os.environ.get("STARLIGHT_DATA_LOCATION", "us-central1")
BUCKET = os.environ.get("KMARKET_OKF_BUCKET", "kmarket_okf")
PREFIX = os.environ.get("STARLIGHT_OKF_PREFIX", "okf")


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _access_token() -> str:
    # ADC with retries; gcloud only when installed (app/gcp_auth.py, runbook S13 pitfall).
    return gcp_auth.access_token()


def _mask_str(val: Any) -> Any:
    if not isinstance(val, str):
        return val
    return (
        val.replace(f"gs://{BUCKET}/{PREFIX}/", "gs://okf/")
        .replace(f"gs://{BUCKET}/", "gs://okf/")
        .replace(f"storage.googleapis.com/{BUCKET}/{PREFIX}/", "storage.googleapis.com/okf/")
        .replace(f"storage.googleapis.com/{BUCKET}/", "storage.googleapis.com/okf/")
        .replace(f"{PROJECT}.", "")
        .replace(PROJECT, "kmarket-gcp-project")
        .replace(f"{PROJECT_ID}.", "")
        .replace(PROJECT_ID, "kmarket-gcp-project")
        .replace(PROJECT_NUMBER, "000000000000")
    )


def run_bq_sql(sql: str, raw: bool = False) -> tuple[list[dict], dict]:
    t0 = time.time()
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/queries"
    req_body = {"query": sql, "useLegacySql": False, "location": LOCATION, "timeoutMs": 25000}
    req = urllib.request.Request(
        url,
        data=json.dumps(req_body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    elapsed_ms = int((time.time() - t0) * 1000)
    fields = [f["name"] for f in data.get("schema", {}).get("fields", [])]
    rows = []
    for r in data.get("rows", []):
        row_dict = {}
        for idx, cell in enumerate(r.get("f", [])):
            col_name = fields[idx] if idx < len(fields) else f"col_{idx}"
            cell_val = cell.get("v")
            row_dict[col_name] = cell_val if raw else _mask_str(cell_val)
        rows.append(row_dict)

    meta = {
        "job_id": data.get("jobReference", {}).get("jobId", "bqjob_live"),
        "elapsed_ms": elapsed_ms,
        "total_bytes": int(data.get("totalBytesProcessed", "0") or 0),
        "cache_hit": bool(data.get("cacheHit", False)),
        "row_count": len(rows),
        "executed_at": _now_iso(),
    }
    return rows, meta


def _split_okf_markdown(md_text: str) -> tuple[str, str]:
    """Splits a raw OKF markdown file into (yaml_frontmatter, verbatim_body)."""
    text = (md_text or "").lstrip("\ufeff")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[1].strip(), parts[2].strip()
    return "", text.strip()


def resolve_bq_objectrefs_live(prov_slots: list[str], doc_ids: list[str], dataset: str = "kmarket_ontology") -> tuple[dict[str, dict], dict]:
    """Resolves BigQuery ObjectRef (`gcs_obj_ref`) via `OBJ.FETCH_METADATA` and `OBJ.GET_ACCESS_URL`
    in live BigQuery, then fetches the live OKF Markdown from GCS using the BigQuery-signed `read_url`.
    """
    prov_clean = sorted({s for s in prov_slots if s})
    doc_clean = sorted({d for d in doc_ids if d})
    subqueries = []
    if prov_clean:
        p_in = ", ".join(f"'{s}'" for s in prov_clean)
        subqueries.append(f"""
        SELECT
          'PROVISION' AS node_kind,
          provision_slot_id AS key_id,
          TO_JSON_STRING(OBJ.FETCH_METADATA(gcs_obj_ref)) AS obj_meta_json,
          TO_JSON_STRING(OBJ.GET_ACCESS_URL(gcs_obj_ref, 'r')) AS access_url_json
        FROM `{PROJECT}.{dataset}.v_node_provision`
        WHERE provision_slot_id IN ({p_in})
        """)
    if doc_clean:
        d_in = ", ".join(f"'{d}'" for d in doc_clean)
        subqueries.append(f"""
        SELECT
          'DOC' AS node_kind,
          doc_id AS key_id,
          TO_JSON_STRING(OBJ.FETCH_METADATA(gcs_obj_ref)) AS obj_meta_json,
          TO_JSON_STRING(OBJ.GET_ACCESS_URL(gcs_obj_ref, 'r')) AS access_url_json
        FROM `{PROJECT}.{dataset}.v_node_source_document`
        WHERE doc_id IN ({d_in})
        """)
    if not subqueries:
        return {}, {}

    obj_sql = "\nUNION ALL\n".join(subqueries)
    obj_rows, obj_meta = run_bq_sql(obj_sql, raw=True)

    def _fetch_single_gcs_object(row: dict) -> tuple[str, dict]:
        kind = row.get("node_kind", "")
        key_id = row.get("key_id", "")
        map_key = f"{kind}::{key_id}"
        meta_obj = json.loads(row.get("obj_meta_json") or "{}")
        url_obj = json.loads(row.get("access_url_json") or "{}")
        details_raw = meta_obj.get("details") or {}
        if isinstance(details_raw, str):
            try:
                details_raw = json.loads(details_raw)
            except Exception:
                details_raw = {}
        gcs_details = details_raw.get("gcs_metadata") or details_raw or {}
        access_urls = url_obj.get("access_urls") or {}
        read_url = access_urls.get("read_url") or ""
        expiry_time = access_urls.get("expiry_time") or ""

        raw_md = ""
        if read_url:
            with urllib.request.urlopen(read_url, timeout=10) as gcs_resp:
                raw_md = gcs_resp.read().decode("utf-8")

        fm_str, body_str = _split_okf_markdown(raw_md)
        masked_uri = _mask_str(str(meta_obj.get("uri") or ""))
        masked_auth = _mask_str(str(meta_obj.get("authorizer") or ""))
        version_gen = str(meta_obj.get("version") or "")

        gcs_obj_ref_struct = {
            "uri": masked_uri,
            "version": version_gen,
            "authorizer": masked_auth,
            "details": {
                "content_type": str(gcs_details.get("content_type") or "text/markdown"),
                "md5_hash": str(gcs_details.get("md5_hash") or ""),
                "size": int(gcs_details.get("size") or 0),
                "updated": int(gcs_details.get("updated") or 0),
            },
        }
        live_info = {
            "resolved_via": "OBJ.FETCH_METADATA(gcs_obj_ref) + OBJ.GET_ACCESS_URL(gcs_obj_ref, 'r')",
            "bq_job_id": obj_meta.get("job_id", ""),
            "bq_elapsed_ms": obj_meta.get("elapsed_ms", 0),
            "uri": masked_uri,
            "version": version_gen,
            "authorizer": masked_auth,
            "content_type": str(gcs_details.get("content_type") or "text/markdown"),
            "size_bytes": int(gcs_details.get("size") or 0),
            "md5_hash": str(gcs_details.get("md5_hash") or ""),
            "updated_ts": int(gcs_details.get("updated") or 0),
            "signed_url_expiry": str(expiry_time),
            "signed_read_url_masked": _mask_str(read_url)[:96] + "..." if read_url else "",
            "yaml_frontmatter": _mask_str(fm_str),
            "verbatim_body": _mask_str(body_str),
        }
        return map_key, {"gcs_obj_ref": gcs_obj_ref_struct, "objectRefLive": live_info}

    resolved_map: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_fetch_single_gcs_object, r) for r in obj_rows]
        for fut in concurrent.futures.as_completed(futures):
            try:
                mk, val = fut.result()
                resolved_map[mk] = val
            except Exception:
                traceback.print_exc()

    return resolved_map, obj_meta
