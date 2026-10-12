#!/usr/bin/env python3
"""Enterprise Web Studio Server (`localhost:8090`) with Real-Time GCS & Dataplex Knowledge Catalog Sync.

Serves static files from `/home/changseop/finance_ontology/` AND exposes REST APIs:
  - GET  /api/okf/state         : Returns live KC registry state + version history + modified files
  - POST /api/okf/publish       : Publishes single edited OKF file -> archives old version to GCS `versions/`,
                                  overwrites canonical GCS path, marks old KC entry `deprecated`,
                                  and registers new versioned KC entry as `verified`.
  - POST /api/okf/batch_publish : Executes batch frontmatter update & KC registration for multiple selected files.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import subprocess
import sys
import tempfile
import traceback
import urllib.error
from urllib.parse import quote, urlencode, urlparse
import urllib.request
import yaml

_TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
if _TOOLS_DIR not in sys.path:
    sys.path.insert(0, _TOOLS_DIR)

ROOT = os.environ.get("STARLIGHT_STUDIO_ROOT") or os.path.dirname(_TOOLS_DIR)
OKF_DIR = os.path.join(ROOT, "finance", "okf")
VERSIONS_DIR = os.path.join(OKF_DIR, "versions")
STATE_FILE = os.path.join(ROOT, "tools", "kc_registry_state.json")

PROJECT = os.environ.get("STARLIGHT_GCP_PROJECT", "finance-ontology-changseop")
PROJECT_NUMBER = os.environ.get("STARLIGHT_GCP_PROJECT_NUMBER", "567090080191")
LOCATION = os.environ.get("STARLIGHT_GCP_LOCATION", "us-central1")
ENTRY_GROUP = os.environ.get("STARLIGHT_KC_ENTRY_GROUP", "finance-okf")
ENTRY_TYPE = os.environ.get("STARLIGHT_KC_ENTRY_TYPE", "okf-bundle")
BUCKET = os.environ.get("STARLIGHT_OKF_BUCKET", "finance_okf")
PREFIX = os.environ.get("STARLIGHT_OKF_PREFIX", "okf")
ALLOW_PUBLISH = os.environ.get("STARLIGHT_ALLOW_PUBLISH", "true").strip().lower() in (
    "1",
    "true",
    "yes",
)

OKF_ASPECT = f"{PROJECT_NUMBER}.{LOCATION}.okf"
OVERVIEW_ASPECT = "dataplex-types.global.overview"
CONTACTS_ASPECT = "dataplex-types.global.contacts"

# DR-05 (2026-09-27): VERSIONS_DIR is created lazily in process_single_publish(). Creating it at
# import left an empty okf/versions/ without index.md, which made okf_lint FAIL on the workspace.


def parse_contacts_aspect(raw_contacts) -> dict | None:
    if not raw_contacts:
        return None
    s = str(raw_contacts).strip()
    if not s or s == "-":
        return None
    import re
    m = re.match(r"^(.+?)\s*<([^>]+)>$", s)
    if m:
        name_part = m.group(1).strip()
        email_part = m.group(2).strip()
    else:
        name_part = s
        email_part = ""
    role = (
        "owner"
        if any(k in name_part for k in ("봉미선", "여신심사", "박서준", "MD본부", "최유진", "그로스마케팅", "AI추천랩"))
        else "steward"
    )
    return {
        "identities": [
            {
                "role": role,
                "name": name_part,
                "id": email_part or name_part,
            }
        ]
    }


def now_iso() -> str:
    return (
        _dt.datetime.now(_dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def bump_semver(current_ver: str, level: str) -> str:
    parts = [int(x) if x.isdigit() else 0 for x in str(current_ver or "0.2.0").split(".")]
    while len(parts) < 3:
        parts.append(0)
    major, minor, patch = parts[0], parts[1], parts[2]
    lvl = (level or "PATCH").upper()
    if lvl == "MAJOR":
        return f"{major + 1}.0.0"
    if lvl == "MINOR":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def make_safe_entry_id(raw: str) -> str:
    import re
    s = re.sub(r"[^a-z0-9_-]", "-", raw.lower()).strip("-")
    s = re.sub(r"-+", "-", s)
    if not s or not s[0].isalpha():
        s = "e-" + s
    if len(s) <= 63:
        return s
    h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]
    return f"{s[:54].rstrip('-')}-{h}"


STATE_GCS_OBJ = "studio_state/kc_registry_state.json"


def load_state() -> dict:
    # 1. Read canonical registry state from GCS so Cloud Run instances / restarts stay in sync
    try:
        tok = get_gcloud_token()
        if tok:
            url = (
                f"https://storage.googleapis.com/storage/v1/b/{quote(BUCKET, safe='')}/o/"
                f"{quote(STATE_GCS_OBJ, safe='')}?alt=media"
            )
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read().decode("utf-8")
                data = json.loads(raw)
                if isinstance(data, dict) and "files" in data:
                    try:
                        with open(STATE_FILE, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                    return data
    except Exception:
        pass

    # 2. Fallback to local STATE_FILE
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"files": {}, "deprecated_entries": []}


def save_state(st: dict) -> None:
    payload = json.dumps(st, ensure_ascii=False, indent=2).encode("utf-8")
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write(payload.decode("utf-8"))
    except Exception:
        pass
    try:
        tok = get_gcloud_token()
        if tok:
            url = (
                f"https://storage.googleapis.com/upload/storage/v1/b/{quote(BUCKET, safe='')}/o"
                f"?uploadType=media&name={quote(STATE_GCS_OBJ, safe='')}"
            )
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {tok}",
                    "Content-Type": "application/json; charset=utf-8",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                _ = resp.read()
    except Exception:
        pass


_TOKEN_CACHE = {"token": "", "exp": 0.0}


def get_gcloud_token() -> str:
    import time
    from agent_remote_client import _access_token

    now = time.time()
    if _TOKEN_CACHE["token"] and now < _TOKEN_CACHE["exp"]:
        return _TOKEN_CACHE["token"]
    tok = _access_token()
    if tok:
        _TOKEN_CACHE["token"] = tok
        _TOKEN_CACHE["exp"] = now + 1200.0
    return tok


def upload_to_gcs(local_path: str, gcs_rel_path: str) -> dict:
    obj_name = f"{PREFIX}/{gcs_rel_path}".lstrip("/")
    url = (
        f"https://storage.googleapis.com/upload/storage/v1/b/{quote(BUCKET, safe='')}/o"
        f"?uploadType=media&name={quote(obj_name, safe='')}"
    )
    try:
        with open(local_path, "rb") as f:
            payload = f.read()
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {get_gcloud_token()}",
                "Content-Type": "text/markdown; charset=utf-8",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            _ = resp.read()
        return {
            "ok": True,
            "gcs_masked": f"gs://okf/{gcs_rel_path}",
            "stderr": "",
        }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")[:240]
        return {
            "ok": False,
            "gcs_masked": f"gs://okf/{gcs_rel_path}",
            "stderr": f"HTTP {e.code}: {err_body}",
        }
    except Exception as e:
        return {
            "ok": False,
            "gcs_masked": f"gs://okf/{gcs_rel_path}",
            "stderr": str(e)[:240],
        }


def upsert_dataplex_entry(
    entry_id: str,
    gcs_rel_path: str,
    title: str,
    fm_meta: dict,
    markdown_body: str,
) -> dict:
    gcs_uri = f"gs://{BUCKET}/{PREFIX}/{gcs_rel_path}"
    ts = fm_meta.get("verified_at") or now_iso()

    aspect_payload = {
        "okf_type": str(fm_meta.get("kind") or fm_meta.get("type") or "Provision"),
        "version": str(fm_meta.get("version", "0.2.0")),
        "status": str(fm_meta.get("status", "verified")),
        "generated": {
            "by": str(fm_meta.get("generated_by", "process:build_okf/3.0")),
            "at": str(fm_meta.get("generated_at", ts)),
        },
        "verified": [
            {
                "by": str(fm_meta.get("verified_by", "compliance_reviewer")),
                "at": ts,
                "method": str(fm_meta.get("verified_method", "source_text_match")),
                "checks": "P1_body, P2_heading, P3_page, P4_digest",
            }
        ],
        "sources": [
            {
                "id": "origin_pdf",
                "resource": str(fm_meta.get("source_resource") or fm_meta.get("source_uri") or gcs_uri),
                "title": title,
                "kind": "origin_document",
                "sha256": str(fm_meta.get("sha256", "")),
            }
        ],
        "content_class": str(fm_meta.get("content_class", "authentic")),
        "treatment": str(fm_meta.get("treatment", "verbatim_ko")),
        "language": "ko",
        "license": str(fm_meta.get("license") or fm_meta.get("authority") or "공공누리 제1유형"),
        "part_of": str(fm_meta.get("part_of", "")),
        "section_number": str(fm_meta.get("section_number", "")),
        "source_page": str(fm_meta.get("source_page", "1")),
        "extra": json.dumps(
            {
                "superseded_by": str(fm_meta.get("superseded_by", "")),
                "supersedes": str(fm_meta.get("supersedes", "")),
                "change_note": str(fm_meta.get("change_note", "")),
            },
            ensure_ascii=False,
        ),
    }

    aspects = {
        OKF_ASPECT: {"data": aspect_payload},
        OVERVIEW_ASPECT: {
            "data": {
                "content": markdown_body.strip() or f"# {title}",
                "contentType": "MARKDOWN",
            }
        },
    }
    contacts_data = parse_contacts_aspect(fm_meta.get("contacts"))
    if contacts_data:
        aspects[CONTACTS_ASPECT] = {"data": contacts_data}

    desc = f"{fm_meta.get('domain', 'finance')} · v{fm_meta.get('version', '0.2.0')} ({fm_meta.get('status', 'verified')})"
    parent = f"projects/{PROJECT}/locations/{LOCATION}/entryGroups/{ENTRY_GROUP}"
    entry_name = f"{parent}/entries/{entry_id}"
    entry_type_ref = f"projects/{PROJECT}/locations/{LOCATION}/entryTypes/{ENTRY_TYPE}"
    token = get_gcloud_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    create_url = f"https://dataplex.googleapis.com/v1/{parent}/entries?entryId={quote(entry_id, safe='')}"
    create_body = {
        "name": entry_name,
        "entryType": entry_type_ref,
        "aspects": aspects,
        "entrySource": {
            "resource": gcs_uri,
            "system": "Open Knowledge Format",
            "platform": "OKF",
            "displayName": title[:240],
            "description": desc[:900],
            "updateTime": ts,
        },
    }
    try:
        req = urllib.request.Request(
            create_url,
            data=json.dumps(create_body, ensure_ascii=False, default=str).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            _ = resp.read()
        return {"ok": True, "action": "CREATED", "entry_id": entry_id}
    except urllib.error.HTTPError as e:
        if e.code != 409:
            err_body = e.read().decode("utf-8", errors="ignore")[:300]
            return {
                "ok": False,
                "action": "CREATE_FAILED",
                "entry_id": entry_id,
                "stderr": f"HTTP {e.code}: {err_body}",
            }
    except Exception as e:
        return {
            "ok": False,
            "action": "CREATE_FAILED",
            "entry_id": entry_id,
            "stderr": str(e)[:300],
        }

    # Entry already exists (409) -> PATCH entry
    query_params = [
        (
            "updateMask",
            "aspects,entry_source.description,entry_source.display_name,entry_source.resource,entry_source.update_time",
        )
    ] + [("aspectKeys", k) for k in sorted(aspects.keys())]
    patch_url = (
        f"https://dataplex.googleapis.com/v1/{parent}/entries/{quote(entry_id, safe='/')}"
        f"?{urlencode(query_params)}"
    )
    patch_body = {
        "name": entry_name,
        "aspects": aspects,
        "entrySource": {
            "resource": gcs_uri,
            "displayName": title[:240],
            "description": desc[:900],
            "updateTime": ts,
        },
    }
    try:
        req2 = urllib.request.Request(
            patch_url,
            data=json.dumps(patch_body, ensure_ascii=False, default=str).encode("utf-8"),
            headers=headers,
            method="PATCH",
        )
        with urllib.request.urlopen(req2, timeout=25) as resp2:
            _ = resp2.read()
        return {"ok": True, "action": "UPDATED", "entry_id": entry_id, "stderr": ""}
    except urllib.error.HTTPError as e2:
        err_body = e2.read().decode("utf-8", errors="ignore")[:300]
        return {
            "ok": False,
            "action": "UPDATED",
            "entry_id": entry_id,
            "stderr": f"HTTP {e2.code}: {err_body}",
        }
    except Exception as e2:
        return {
            "ok": False,
            "action": "UPDATED",
            "entry_id": entry_id,
            "stderr": str(e2)[:300],
        }



def process_single_publish(item: dict, st: dict) -> dict:
    rel_path = item["rel_path"].replace("gs://okf/", "").lstrip("/")
    bump_level = item.get("bump_level", "PATCH")
    change_note = item.get("change_note", "프론트매터 거버넌스 속성 및 조문 본문 현행화")
    fm_in = item.get("frontmatter", {})
    new_body = item.get("body", "").strip()

    prev_record = st["files"].get(rel_path, {})
    old_ver = prev_record.get("version") or fm_in.get("old_version") or "0.2.0"
    new_ver = bump_semver(old_ver, bump_level)
    ts = now_iso()

    canonical_eid = rel_path[:-3] if rel_path.endswith(".md") else rel_path
    short_slug = os.path.basename(canonical_eid)
    if short_slug == "doc":
        parent_slug = os.path.basename(os.path.dirname(canonical_eid))
        short_slug = f"{parent_slug}_doc" if parent_slug else "doc"
    old_ver_slug = old_ver.replace(".", "_")
    deprecated_eid = f"versions/{short_slug}_v{old_ver_slug}"
    active_eid = canonical_eid

    abs_md_path = os.path.join(OKF_DIR, rel_path)
    os.makedirs(os.path.dirname(abs_md_path), exist_ok=True)

    # 1. Preserve old file content as a snapshot in `okf/versions/<short_slug>_v<old_ver>.md`
    old_body = prev_record.get("body") or item.get("old_body") or new_body
    old_fm = prev_record.get("frontmatter") or {
        "id": fm_in.get("id", short_slug),
        "title": fm_in.get("old_title") or fm_in.get("title", ""),
        "synonyms": fm_in.get("synonyms", []),
        "kind": fm_in.get("old_kind") or fm_in.get("kind", "Concept"),
        "version": old_ver,
        "domain": fm_in.get("old_domain") or fm_in.get("domain", "finance.supervisory_reg"),
        "status": "deprecated",
        "content_class": fm_in.get("old_content_class") or fm_in.get("content_class", "narrative"),
        "authority": fm_in.get("old_authority") or fm_in.get("authority", "금융위원회"),
        "sensitivity": fm_in.get("old_sensitivity") or fm_in.get("sensitivity", "public"),
        "verified_by": fm_in.get("old_verified_by") or fm_in.get("verified_by", "okf_pipeline_v0.2"),
        "verified_at": fm_in.get("old_verified_at") or "2026-03-29T00:00:00Z",
        "contacts": fm_in.get("old_contacts") or fm_in.get("contacts") or "",
        "sha256": hashlib.sha256(old_body.encode("utf-8")).hexdigest()[:16],
        "locations": fm_in.get("locations", "locations.yaml"),
        "source_uri": fm_in.get("source_uri", f"gs://okf/{rel_path}"),
        "superseded_by": f"{active_eid} (v{new_ver})",
        "change_note": f"Superseded by v{new_ver}: {change_note}",
    }

    snapshot_rel = f"versions/{short_slug}_v{old_ver}.md"
    snapshot_abs = os.path.join(OKF_DIR, snapshot_rel)
    old_yaml_doc = {
        "id": old_fm["id"],
        "title": old_fm["title"],
        "kind": old_fm["kind"],
        "version": old_ver,
        "domain": old_fm["domain"],
        "status": "deprecated",
        "content_class": old_fm["content_class"],
        "authority": old_fm["authority"],
        "sensitivity": old_fm["sensitivity"],
        "verified": {"by": old_fm["verified_by"], "at": old_fm["verified_at"]},
        "superseded_by": f"v{new_ver} ({ts})",
        "sha256": old_fm["sha256"],
    }
    if old_fm.get("contacts"):
        old_yaml_doc["contacts"] = old_fm["contacts"]
    snapshot_md = (
        "---\n"
        + yaml.safe_dump(old_yaml_doc, allow_unicode=True, sort_keys=False)
        + "---\n\n"
        + f"> **[DEPRECATED SNAPSHOT · v{old_ver}]** 이 엔트리는 `{ts}`에 배포된 **v{new_ver}**(`gs://okf/{rel_path}`)에 의해 만료(Deprecated) 처리되었습니다. (개정 사유: {change_note})\n\n"
        + old_body
        + "\n"
    )
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    with open(snapshot_abs, "w", encoding="utf-8") as f:
        f.write(snapshot_md)

    # 2. Write new versioned file to canonical path `okf/<rel_path>`
    new_sha = hashlib.sha256(new_body.encode("utf-8")).hexdigest()[:16]
    new_fm = {
        "id": fm_in.get("id", short_slug),
        "title": fm_in.get("title", ""),
        "synonyms": fm_in.get("synonyms", []),
        "kind": fm_in.get("kind", "Concept"),
        "version": new_ver,
        "domain": fm_in.get("domain", "finance.supervisory_reg"),
        "status": fm_in.get("status", "verified"),
        "content_class": fm_in.get("content_class", "narrative"),
        "authority": fm_in.get("authority", "금융위원회"),
        "sensitivity": fm_in.get("sensitivity", "public"),
        "verified_by": fm_in.get("verified_by", "compliance_reviewer"),
        "verified_at": ts,
        "contacts": fm_in.get("contacts") or "",
        "sha256": new_sha,
        "locations": fm_in.get("locations", "locations.yaml"),
        "source_uri": fm_in.get("source_uri", f"gs://okf/{rel_path}"),
        "supersedes": f"{deprecated_eid} (v{old_ver})",
        "change_note": change_note,
    }

    new_yaml_doc = {
        "id": new_fm["id"],
        "title": new_fm["title"],
        "synonyms": new_fm["synonyms"],
        "kind": new_fm["kind"],
        "version": new_ver,
        "domain": new_fm["domain"],
        "status": new_fm["status"],
        "content_class": new_fm["content_class"],
        "authority": new_fm["authority"],
        "sensitivity": new_fm["sensitivity"],
        "verified": {"by": new_fm["verified_by"], "at": ts},
        "sha256": new_sha,
        "locations": new_fm["locations"],
        "source_uri": new_fm["source_uri"],
    }
    if new_fm.get("contacts"):
        new_yaml_doc["contacts"] = new_fm["contacts"]
    canonical_md = (
        "---\n"
        + yaml.safe_dump(new_yaml_doc, allow_unicode=True, sort_keys=False)
        + "---\n\n"
        + new_body
        + "\n"
    )
    with open(abs_md_path, "w", encoding="utf-8") as f:
        f.write(canonical_md)

    # 3. Real GCS Upload (both snapshot and canonical file)
    gcs_snap_res = upload_to_gcs(snapshot_abs, snapshot_rel)
    gcs_main_res = upload_to_gcs(abs_md_path, rel_path)

    # 4. Real Dataplex Knowledge Catalog API Updates:
    #    4a) Register/Update Deprecated Entry (`<base_eid>-v0_2_0`) pointing to `gs://okf/versions/...` with status=deprecated
    kc_dep_res = upsert_dataplex_entry(
        deprecated_eid,
        snapshot_rel,
        f"[DEPRECATED v{old_ver}] {old_fm['title']}",
        old_fm,
        snapshot_md.split("---\n\n", 1)[-1],
    )
    #    4b) Update Active Canonical Entry (`<base_eid>`) pointing to `gs://okf/<rel_path>` with status=verified & new version
    kc_act_res = upsert_dataplex_entry(
        active_eid,
        rel_path,
        new_fm["title"],
        new_fm,
        f"> **[ACTIVE · v{new_ver}]** Updated at `{ts}` by `{new_fm['verified_by']}` (Supersedes `v{old_ver}` · 사유: {change_note})\n\n" + new_body,
    )

    # 5. Persist in state
    dep_record = {
        "entry_id": deprecated_eid,
        "rel_path": snapshot_rel,
        "canonical_rel_path": rel_path,
        "version": old_ver,
        "status": "deprecated",
        "deprecated_at": ts,
        "superseded_by": active_eid,
        "superseded_by_version": new_ver,
        "change_note": change_note,
        "frontmatter": old_fm,
        "body": old_body,
    }
    st["deprecated_entries"].insert(0, dep_record)
    st["files"][rel_path] = {
        "entry_id": active_eid,
        "rel_path": rel_path,
        "version": new_ver,
        "prev_version": old_ver,
        "status": new_fm["status"],
        "updated_at": ts,
        "change_note": change_note,
        "supersedes_entry_id": deprecated_eid,
        "frontmatter": new_fm,
        "body": new_body,
        "history_count": prev_record.get("history_count", 0) + 1,
    }

    return {
        "ok": True,
        "rel_path": rel_path,
        "old_version": old_ver,
        "new_version": new_ver,
        "bump_level": bump_level,
        "updated_at": ts,
        "deprecated_entry_id": deprecated_eid,
        "active_entry_id": active_eid,
        "snapshot_gcs_uri": f"gs://okf/{snapshot_rel}",
        "canonical_gcs_uri": f"gs://okf/{rel_path}",
        "gcs_sync": gcs_main_res["ok"] and gcs_snap_res["ok"],
        "kc_deprecated_sync": kc_dep_res["ok"],
        "kc_active_sync": kc_act_res["ok"],
        "frontmatter": new_fm,
    }


def _mask_str(val):
    if not isinstance(val, str):
        return val
    return (
        val.replace(f"gs://{BUCKET}/{PREFIX}/", "gs://okf/")
        .replace(f"gs://{BUCKET}/", "gs://okf/")
        .replace("gs://kmarket_okf/okf/", "gs://okf/")
        .replace("gs://kmarket_okf/", "gs://okf/")
        .replace(f"storage.googleapis.com/{BUCKET}/{PREFIX}/", "storage.googleapis.com/okf/")
        .replace(f"storage.googleapis.com/{BUCKET}/", "storage.googleapis.com/okf/")
        .replace("storage.googleapis.com/kmarket_okf/okf/", "storage.googleapis.com/okf/")
        .replace("storage.googleapis.com/kmarket_okf/", "storage.googleapis.com/okf/")
        .replace(f"{PROJECT}.", "")
        .replace(PROJECT, "starlight-gcp-project")
        .replace(PROJECT_NUMBER, "000000000000")
    )


def _mask_dict(d: dict) -> dict:
    return {k: _mask_str(v) for k, v in d.items()}


def run_bq_sql(sql: str, raw: bool = False) -> tuple[list[dict], dict]:
    import time
    import urllib.request

    t0 = time.time()
    token = get_gcloud_token()
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{PROJECT}/queries"
    req_body = {
        "query": sql,
        "useLegacySql": False,
        "location": LOCATION,
        "timeoutMs": 25000,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(req_body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
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
        "executed_at": now_iso(),
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


def resolve_bq_objectrefs_live(
    prov_slots: list[str], doc_ids: list[str], dataset: str = "starlight_bank_ontology"
) -> tuple[dict[str, dict], dict]:
    """Resolves BigQuery ObjectRef (`gcs_obj_ref`) via `OBJ.FETCH_METADATA` and `OBJ.GET_ACCESS_URL`
    in live BigQuery, then fetches the live OKF Markdown from GCS using the BigQuery-signed `read_url`.
    """
    import concurrent.futures
    import urllib.request

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


def execute_live_bq_graph_query(payload: dict) -> dict:
    import concurrent.futures
    import re

    gql = str(payload.get("gql") or "").strip()
    if payload.get("project") == "ecommerce-ontology" or "kmarket_ontology" in gql:
        from ecommerce_agent_handler import execute_ecommerce_bq_graph_query
        return execute_ecommerce_bq_graph_query(payload, run_bq_sql, resolve_bq_objectrefs_live)

    q_idx = int(payload.get("queryIdx", 0) or 0)

    # Detect which GQL pattern is being executed (supports user edits in GQL editor)
    gql_lower = gql.lower()
    if "provision-criteria" in gql_lower or "제29조" in gql or "ksic_section_code" in gql_lower:
        mode = "CQ01"
    elif "delinquency-rate" in gql_lower or "has_delinquency" in gql_lower or "write_off_yn" in gql_lower:
        mode = "CQ07"
    elif "eod-deferral" in gql_lower or "내규 제16조" in gql or "has_workout_history" in gql_lower:
        mode = "CQ09"
    elif "loan-rate" in gql_lower or "has_rate_cut_request" in gql_lower or "내규 제25조" in gql:
        mode = "CQ12"
    else:
        mode = ["CQ01", "CQ07", "CQ09", "CQ12"][q_idx % 4]

    mode_targets = {
        "CQ01": (
            [
                "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
                "distractors/09_fsc_savings_bank_reg/sec01_savings_bank_soundness_and_art38/distractor_04_art38_provision_surcharge",
            ],
            ["DOC_01_FSC_BANK_REG", "DOC_09_DISTRACTOR_SAVINGS_BANK"],
        ),
        "CQ07": (
            [
                "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_14_ews_delinquency",
                "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_027",
            ],
            ["DOC_10_SYNTHETIC_BYULBIT_POLICY", "DOC_01_FSC_BANK_REG"],
        ),
        "CQ09": (
            [
                "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_16_eod_notice_rule",
                "internal_policies/10_byulbit_bank_credit_rate_policy/ch01_ews_delinquency_and_eod_waiver/internal_art_18_workout_kodit_waiver",
            ],
            ["DOC_10_SYNTHETIC_BYULBIT_POLICY"],
        ),
        "CQ12": (
            [
                "regulations/05_fsc_kfb_loan_rate_reform/ch02_rate_cut_and_abc_disclosure/rate_reform_sec_2_1_b_patent_discretion",
                "internal_policies/10_byulbit_bank_credit_rate_policy/ch02_contract_dates_and_rate_discretion/internal_art_25_tcb_and_patent_exclusion",
            ],
            ["DOC_05_FSC_KFB_RATE", "DOC_10_SYNTHETIC_BYULBIT_POLICY"],
        ),
    }
    target_provs, target_docs = mode_targets.get(mode, ([], []))

    nodes_map: dict[str, dict] = {}
    edges_list: list[dict] = []
    seen_edges: set[tuple[str, str, str]] = set()

    def add_node(node_id: str, node_obj: dict):
        if node_id not in nodes_map:
            nodes_map[node_id] = node_obj

    def add_edge(src: str, dst: str, label: str, color: str = "#6b88a8", width: float = 1.8, dashes: bool = False):
        key = (src, dst, label)
        if key not in seen_edges and src in nodes_map and dst in nodes_map:
            seen_edges.add(key)
            edges_list.append({
                "from": src,
                "to": dst,
                "label": label,
                "color": color,
                "width": width,
                "dashes": dashes,
            })

    obj_executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    obj_future = obj_executor.submit(resolve_bq_objectrefs_live, target_provs, target_docs)

    if mode == "CQ01":
        # Parse KSIC filter from GQL if edited by user
        m_ksic = re.search(r"ksic_section_code\s+IN\s*\(([^)]+)\)", gql, re.IGNORECASE)
        ksic_in = m_ksic.group(1) if m_ksic else "'F', 'G', 'H', 'L'"
        sql = f"""
        SELECT
          ctx.context_id, ctx.dept_name, ctx.purpose_summary,
          inv.term_key, inv.invocation_reason,
          sp.portfolio_scope_rule,
          pr.provision_slot_id, pr.article_no, pr.title AS prov_title, pr.provision_role, pr.target_columns, pr.gcs_uri AS prov_gcs,
          doc.doc_id, doc.title AS doc_title, doc.authority_level, doc.applicable_sector, doc.gcs_uri AS doc_gcs,
          dist.provision_slot_id AS dist_slot_id, dist.article_no AS dist_article_no, dist.title AS dist_title, dist.provision_role AS dist_role,
          dist_doc.doc_id AS dist_doc_id, dist_doc.title AS dist_doc_title, dist_doc.authority_level AS dist_doc_auth, dist_doc.applicable_sector AS dist_doc_sector,
          l.contract_id, l.customer_id, l.product_code, l.borrower_name, l.ksic_section_code, l.asset_classification,
          l.outstanding_amt, l.booked_provision_krw, l.account_status,
          c.industry_name, c.credit_rating,
          fp.product_name, fp.loan_category, fp.base_rate_benchmark
        FROM `{PROJECT}.starlight_bank_ontology.v_node_business_context` ctx
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_invokes_provision` inv
          ON ctx.context_id = inv.context_id AND inv.term_key = 'provision-criteria'
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_provision` pr
          ON inv.provision_slot_id = pr.provision_slot_id AND pr.article_no = '제29조'
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_part_of_document` pod
          ON pr.provision_slot_id = pod.provision_slot_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_source_document` doc
          ON pod.doc_id = doc.doc_id
        LEFT JOIN `{PROJECT}.starlight_bank_ontology.v_edge_conflicts_by_sector` conf
          ON pr.provision_slot_id = conf.bank_slot_id
        LEFT JOIN `{PROJECT}.starlight_bank_ontology.v_node_provision` dist
          ON conf.distractor_slot_id = dist.provision_slot_id
        LEFT JOIN `{PROJECT}.starlight_bank_ontology.v_edge_part_of_document` dist_pod
          ON dist.provision_slot_id = dist_pod.provision_slot_id
        LEFT JOIN `{PROJECT}.starlight_bank_ontology.v_node_source_document` dist_doc
          ON dist_pod.doc_id = dist_doc.doc_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_governed_by_criteria` gov
          ON pr.provision_slot_id = gov.provision_slot_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_loan_contract` l
          ON gov.contract_id = l.contract_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_scopes_portfolio` sp
          ON ctx.context_id = sp.context_id AND l.contract_id = sp.contract_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_customer` c
          ON l.customer_id = c.customer_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_financial_product` fp
          ON l.product_code = fp.product_code
        WHERE ctx.context_id = 'RISK_MGMT'
          AND l.asset_classification = 'NORMAL'
          AND l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
          AND c.ksic_section_code IN ({ksic_in})
        ORDER BY l.contract_id
        """
        rows, meta = run_bq_sql(sql)
        for r in rows:
            ctx_id = f"CTX::{r['context_id']}"
            add_node(ctx_id, {
                "id": ctx_id, "classLabel": "BusinessContext", "layer": "ONT",
                "label": f"[BusinessContext]\n{r['context_id']} ({r['dept_name']})",
                "title": f"v_node_business_context · {r['context_id']}",
                "color": "#4a6fa5", "shape": "box", "viewName": "v_node_business_context",
                "sourceStore": "BigQuery Live (v_node_business_context)",
                "record": {"context_id": r["context_id"], "dept_name": r["dept_name"], "term_key": r["term_key"], "purpose_summary": r["purpose_summary"]},
                "verdictNote": f"Glossary term_key='{r['term_key']}'로 {r['article_no']} 호출 및 ON_BS_CORPORATE_PORTFOLIO 스코핑",
            })
            prov_id = f"PROV::{r['article_no']}"
            add_node(prov_id, {
                "id": prov_id, "classLabel": "Provision", "layer": "LEX",
                "label": f"[Provision · {r['article_no']}]\n{r['prov_title']}",
                "title": f"v_node_provision · {r['article_no']}",
                "color": "#3b735b", "shape": "box", "matchSec": r["article_no"], "viewName": "v_node_provision",
                "sourceStore": "BigQuery Live (v_node_provision) + Dataplex KC Aspect",
                "record": {"provision_slot_id": r["provision_slot_id"], "article_no": r["article_no"], "title": r["prov_title"], "provision_role": r["provision_role"], "target_columns": r["target_columns"], "gcs_uri": r["prov_gcs"]},
                "verdictNote": "정상 0.85% 본칙 및 F·G·H·L 업종 0.90% 단서 규정",
            })
            doc_id = f"DOC::{r['doc_id']}"
            add_node(doc_id, {
                "id": doc_id, "classLabel": "SourceDocument", "layer": "LEX",
                "label": f"[SourceDocument]\n{r['doc_id']}\n({r['authority_level']} · {r['applicable_sector']})",
                "title": f"v_node_source_document · {r['doc_id']}",
                "color": "#477a63", "shape": "box", "matchDocId": r["doc_id"], "viewName": "v_node_source_document",
                "sourceStore": "BigQuery Live (v_node_source_document)",
                "record": {"doc_id": r["doc_id"], "title": r["doc_title"], "authority_level": r["authority_level"], "applicable_sector": r["applicable_sector"], "gcs_uri": r["doc_gcs"]},
                "verdictNote": "조문이 소속된 상위 법령·규정 문서 루트 (PART_OF_DOCUMENT)",
            })
            add_edge(ctx_id, prov_id, f"INVOKES_PROVISION\n[term_key: {r['term_key']}]", "#b88a44", 2.4)
            add_edge(prov_id, doc_id, "PART_OF_DOCUMENT", "#5a8770", 2.0)

            if r.get("dist_slot_id"):
                dist_id = f"PROV::{r['dist_article_no']}"
                add_node(dist_id, {
                    "id": dist_id, "classLabel": "Provision", "layer": "LEX",
                    "label": f"[Provision · 교란차단]\n{r['dist_article_no']} ({r['dist_doc_sector']})",
                    "title": f"v_node_provision · {r['dist_article_no']}",
                    "color": "#a85c56", "shape": "box", "matchSec": r["dist_article_no"], "viewName": "v_node_provision",
                    "sourceStore": "BigQuery Live (v_node_provision · DISTRACTOR_RULE)",
                    "record": {"provision_slot_id": r["dist_slot_id"], "article_no": r["dist_article_no"], "title": r["dist_title"], "provision_role": r["dist_role"]},
                    "verdictNote": "CONFLICTS_BY_SECTOR 엣지로 타업권(상호저축은행) 규정 혼입 차단",
                })
                add_edge(prov_id, dist_id, "CONFLICTS_BY_SECTOR", "#a85c56", 2.0, True)
                if r.get("dist_doc_id"):
                    ddoc_id = f"DOC::{r['dist_doc_id']}"
                    add_node(ddoc_id, {
                        "id": ddoc_id, "classLabel": "SourceDocument", "layer": "LEX",
                        "label": f"[SourceDocument]\n{r['dist_doc_id']}\n({r['dist_doc_auth']} · {r['dist_doc_sector']})",
                        "title": f"v_node_source_document · {r['dist_doc_id']}",
                        "color": "#a85c56", "shape": "box", "matchDocId": r["dist_doc_id"], "viewName": "v_node_source_document",
                        "sourceStore": "BigQuery Live (v_node_source_document)",
                        "record": {"doc_id": r["dist_doc_id"], "title": r["dist_doc_title"], "authority_level": r["dist_doc_auth"], "applicable_sector": r["dist_doc_sector"]},
                        "verdictNote": "타업권(SAVINGS_BANK) 교란 원본 문서 루트",
                    })
                    add_edge(dist_id, ddoc_id, "PART_OF_DOCUMENT", "#a85c56", 1.8, True)

            out_amt = int(r["outstanding_amt"] or 0)
            booked = int(r["booked_provision_krw"] or 0)
            req_090 = int(round(out_amt * 0.009))
            gap = max(0, req_090 - booked)
            loan_id = f"LOAN::{r['contract_id']}"
            add_node(loan_id, {
                "id": loan_id, "classLabel": "LoanContract", "layer": "ONT",
                "label": f"[LoanContract]\n{r['contract_id']} {r['borrower_name']}\n(잔액 {out_amt // 100000000}억 · 부족 {gap // 10000:,}만)",
                "title": f"v_node_loan_contract · {r['contract_id']}",
                "color": "#3b6ea5", "shape": "dot", "size": 21, "viewName": "v_node_loan_contract",
                "sourceStore": "Cloud Spanner Federated Live (ont_loan_contracts)",
                "record": {"contract_id": r["contract_id"], "borrower_name": r["borrower_name"], "ksic_section_code": r["ksic_section_code"], "asset_classification": r["asset_classification"], "outstanding_amt": out_amt, "booked_provision_krw": booked, "required_090_krw": req_090, "reserve_gap_krw": gap},
                "verdictNote": f"장부 {booked:,}원(0.85%) vs 제29조 단서 0.90%({req_090:,}원) → 대손준비금 {gap:,}원 추가 적립",
            })
            cust_id = f"CUST::{r['customer_id']}"
            add_node(cust_id, {
                "id": cust_id, "classLabel": "Customer", "layer": "ONT",
                "label": f"[Customer]\n{r['customer_id']} {r['borrower_name']}\n(ksic='{r['ksic_section_code']}' · {r['industry_name']})",
                "title": f"v_node_customer · {r['customer_id']}",
                "color": "#527a9a", "shape": "dot", "size": 16, "viewName": "v_node_customer",
                "sourceStore": "BigQuery Live (v_node_customer)",
                "record": {"customer_id": r["customer_id"], "borrower_name": r["borrower_name"], "ksic_section_code": r["ksic_section_code"], "industry_name": r["industry_name"], "credit_rating": r["credit_rating"]},
                "verdictNote": f"KSIC '{r['ksic_section_code']}' 업종 확인",
            })
            prod_id = f"PROD::{r['product_code']}"
            add_node(prod_id, {
                "id": prod_id, "classLabel": "FinancialProduct", "layer": "ONT",
                "label": f"[FinancialProduct]\n{r['product_code']}\n({r['loan_category']})",
                "title": f"v_node_financial_product · {r['product_code']}",
                "color": "#527a9a", "shape": "dot", "size": 15, "viewName": "v_node_financial_product",
                "sourceStore": "BigQuery Live (v_node_financial_product)",
                "record": {"product_code": r["product_code"], "product_name": r["product_name"], "loan_category": r["loan_category"], "base_rate_benchmark": r["base_rate_benchmark"]},
                "verdictNote": "기업여신 상품 확인",
            })
            add_edge(ctx_id, loan_id, "SCOPES_PORTFOLIO", "#6b88a8", 1.8)
            add_edge(loan_id, prov_id, "GOVERNED_BY_CRITERIA", "#b88a44", 2.0)
            add_edge(loan_id, cust_id, "BORROWED_BY", "#6b88a8", 1.7)
            add_edge(loan_id, prod_id, "OF_PRODUCT", "#6b88a8", 1.5)

    elif mode == "CQ07":
        sql = f"""
        SELECT
          ctx.context_id, ctx.dept_name,
          inv.term_key, inv.invocation_reason,
          sp.portfolio_scope_rule,
          pr.provision_slot_id, pr.article_no, pr.title AS prov_title, pr.provision_role, pr.target_columns, pr.gcs_uri AS prov_gcs,
          doc.doc_id, doc.title AS doc_title, doc.authority_level, doc.applicable_sector,
          l.contract_id, l.borrower_name, l.asset_classification, l.account_status, l.outstanding_amt, l.overdue_days AS loan_overdue_days,
          del.event_id, del.overdue_days, del.overdue_principal_krw, del.write_off_yn
        FROM `{PROJECT}.starlight_bank_ontology.v_node_business_context` ctx
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_invokes_provision` inv
          ON ctx.context_id = inv.context_id AND inv.term_key = 'delinquency-rate'
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_provision` pr
          ON inv.provision_slot_id = pr.provision_slot_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_part_of_document` pod
          ON pr.provision_slot_id = pod.provision_slot_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_source_document` doc
          ON pod.doc_id = doc.doc_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_has_delinquency` hd
          ON TRUE
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_loan_contract` l
          ON hd.contract_id = l.contract_id
        LEFT JOIN `{PROJECT}.starlight_bank_ontology.v_edge_scopes_portfolio` sp
          ON ctx.context_id = sp.context_id AND l.contract_id = sp.contract_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_delinquency_event` del
          ON hd.event_id = del.event_id
        WHERE ctx.context_id IN ('CREDIT_MGMT', 'DISCLOSURE', 'RISK_MGMT')
          AND pr.article_no IN ('내규 제14조', '제27조')
          AND (del.overdue_days >= 10 OR del.write_off_yn = 'Y')
        ORDER BY ctx.context_id, del.overdue_days DESC
        """
        rows, meta = run_bq_sql(sql)
        for r in rows:
            ctx_id = f"CTX::{r['context_id']}"
            add_node(ctx_id, {
                "id": ctx_id, "classLabel": "BusinessContext", "layer": "ONT",
                "label": f"[BusinessContext]\n{r['context_id']} ({r['dept_name']})",
                "title": f"v_node_business_context · {r['context_id']}",
                "color": "#4a6fa5", "shape": "box", "viewName": "v_node_business_context",
                "sourceStore": "BigQuery Live (v_node_business_context)",
                "record": {"context_id": r["context_id"], "dept_name": r["dept_name"], "term_key": r["term_key"], "invocation_reason": r["invocation_reason"]},
                "verdictNote": r["invocation_reason"],
            })
            prov_id = f"PROV::{r['article_no']}"
            add_node(prov_id, {
                "id": prov_id, "classLabel": "Provision", "layer": "LEX",
                "label": f"[Provision · {r['article_no']}]\n{r['prov_title'][:28]}...",
                "title": f"v_node_provision · {r['article_no']}",
                "color": "#3b735b", "shape": "box", "matchSec": r["article_no"], "viewName": "v_node_provision",
                "sourceStore": "BigQuery Live (v_node_provision) + Dataplex KC Aspect",
                "record": {"provision_slot_id": r["provision_slot_id"], "article_no": r["article_no"], "title": r["prov_title"], "target_columns": r["target_columns"], "gcs_uri": r["prov_gcs"]},
                "verdictNote": r["prov_title"],
            })
            doc_id = f"DOC::{r['doc_id']}"
            add_node(doc_id, {
                "id": doc_id, "classLabel": "SourceDocument", "layer": "LEX",
                "label": f"[SourceDocument]\n{r['doc_id']}\n({r['authority_level']} · {r['applicable_sector']})",
                "title": f"v_node_source_document · {r['doc_id']}",
                "color": "#477a63", "shape": "box", "matchDocId": r["doc_id"], "viewName": "v_node_source_document",
                "sourceStore": "BigQuery Live (v_node_source_document)",
                "record": {"doc_id": r["doc_id"], "title": r["doc_title"], "authority_level": r["authority_level"], "applicable_sector": r["applicable_sector"]},
                "verdictNote": "조문이 소속된 상위 문서 루트 (PART_OF_DOCUMENT)",
            })
            add_edge(ctx_id, prov_id, f"INVOKES_PROVISION\n[term_key: {r['term_key']}]", "#b88a44", 2.2)
            add_edge(prov_id, doc_id, "PART_OF_DOCUMENT", "#5a8770", 1.9)

            is_wo = r["write_off_yn"] == "Y"
            loan_id = f"LOAN::{r['contract_id']}"
            out_amt = int(r["outstanding_amt"] or 0)
            add_node(loan_id, {
                "id": loan_id, "classLabel": "LoanContract", "layer": "ONT",
                "label": f"[LoanContract]\n{r['contract_id']} {r['borrower_name']}\n({r['loan_overdue_days']}일 연체 · {out_amt // 100000000}억)",
                "title": f"v_node_loan_contract · {r['contract_id']}",
                "color": "#a85c56" if is_wo else "#3b6ea5", "shape": "dot", "size": 20, "viewName": "v_node_loan_contract",
                "sourceStore": "Cloud Spanner Federated Live (ont_loan_contracts)",
                "record": {"contract_id": r["contract_id"], "borrower_name": r["borrower_name"], "asset_classification": r["asset_classification"], "account_status": r["account_status"], "outstanding_amt": out_amt, "overdue_days": int(r["loan_overdue_days"] or 0)},
                "verdictNote": "상각특수채권(EWS만 포함)" if is_wo else f"{r['loan_overdue_days']}일 연체 계좌",
            })
            if r.get("portfolio_scope_rule"):
                od_val = int(r["overdue_days"] or 0)
                if (r["context_id"] == "CREDIT_MGMT" and (is_wo or od_val < 30)) or \
                   (r["context_id"] == "DISCLOSURE" and not is_wo and od_val >= 30) or \
                   (r["context_id"] == "RISK_MGMT" and not is_wo and r["asset_classification"] == "SUBSTANDARD"):
                    add_edge(ctx_id, loan_id, "SCOPES_PORTFOLIO", "#6b88a8", 1.6)
            del_id = f"DEL::{r['event_id']}"
            add_node(del_id, {
                "id": del_id, "classLabel": "DelinquencyEvent", "layer": "ONT",
                "label": f"[DelinquencyEvent]\n{r['event_id']} ({r['overdue_days']}일 · write_off={r['write_off_yn']})",
                "title": f"v_node_delinquency_event · {r['event_id']}",
                "color": "#a85c56" if is_wo else "#527a9a", "shape": "dot", "size": 15, "viewName": "v_node_delinquency_event",
                "sourceStore": "Cloud Spanner Federated Live (ont_delinquency_events)",
                "record": {"event_id": r["event_id"], "contract_id": r["contract_id"], "overdue_days": int(r["overdue_days"] or 0), "overdue_principal_krw": int(r["overdue_principal_krw"] or 0), "write_off_yn": r["write_off_yn"]},
                "verdictNote": f"write_off_yn='{r['write_off_yn']}', overdue_days={r['overdue_days']}",
            })
            add_edge(loan_id, del_id, "HAS_DELINQUENCY", "#6b88a8", 1.7)
            if r["article_no"] == "내규 제14조":
                add_edge(loan_id, prov_id, "GOVERNED_BY_CRITERIA", "#b88a44", 1.8)
        if "PROV::제27조" in nodes_map and "PROV::내규 제14조" in nodes_map:
            add_edge("PROV::제27조", "PROV::내규 제14조", "DELEGATES_TO_INTERNAL", "#5a8770", 2.0)

    elif mode == "CQ09":
        m_od = re.search(r"overdue_days\s*>\s*(\d+)", gql, re.IGNORECASE)
        min_od = int(m_od.group(1)) if m_od else 30
        sql = f"""
        SELECT
          ctx.context_id, ctx.dept_name,
          inv.term_key, inv.invocation_reason,
          sp.portfolio_scope_rule,
          pr.provision_slot_id, pr.article_no, pr.title AS prov_title, pr.target_columns, pr.gcs_uri AS prov_gcs,
          doc.doc_id, doc.title AS doc_title, doc.authority_level, doc.applicable_sector,
          l.contract_id, l.borrower_name, l.overdue_days, l.asset_classification, l.rehab_priority_claim_yn, l.outstanding_amt, l.account_status,
          w.workout_id, w.consecutive_normal_repay_months, w.new_equity_paid_in_krw, w.legal_proceeding_code,
          col.collateral_id, col.collateral_type_code, col.guarantee_agency_code, col.guarantee_ratio_pct,
          ea.approval_id, ea.approval_type_code, ea.approval_status, ea.approver_role_code, ea.approval_dt
        FROM `{PROJECT}.starlight_bank_ontology.v_node_business_context` ctx
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_invokes_provision` inv
          ON ctx.context_id = inv.context_id AND inv.term_key = 'eod-deferral'
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_provision` pr
          ON inv.provision_slot_id = pr.provision_slot_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_part_of_document` pod
          ON pr.provision_slot_id = pod.provision_slot_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_source_document` doc
          ON pod.doc_id = doc.doc_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_loan_contract` l
          ON l.overdue_days > {min_od} AND l.account_status != 'WRITTEN_OFF_SPECIAL_CLAIM'
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_scopes_portfolio` sp
          ON ctx.context_id = sp.context_id AND l.contract_id = sp.contract_id
        LEFT JOIN `{PROJECT}.starlight_bank_ontology.v_node_workout_history` w
          ON l.contract_id = w.contract_id
        LEFT JOIN `{PROJECT}.starlight_bank_ontology.v_node_collateral` col
          ON l.contract_id = col.contract_id
        LEFT JOIN `{PROJECT}.starlight_bank_ontology.v_node_exception_approval` ea
          ON l.contract_id = ea.contract_id
        WHERE ctx.context_id = 'CREDIT_MGMT'
        ORDER BY l.contract_id, pr.article_no
        """
        rows, meta = run_bq_sql(sql)
        for r in rows:
            ctx_id = f"CTX::{r['context_id']}"
            add_node(ctx_id, {
                "id": ctx_id, "classLabel": "BusinessContext", "layer": "ONT",
                "label": f"[BusinessContext]\n{r['context_id']} ({r['dept_name']})",
                "title": f"v_node_business_context · {r['context_id']}",
                "color": "#4a6fa5", "shape": "box", "viewName": "v_node_business_context",
                "sourceStore": "BigQuery Live (v_node_business_context)",
                "record": {"context_id": r["context_id"], "dept_name": r["dept_name"], "term_key": r["term_key"]},
                "verdictNote": f"term_key='{r['term_key']}'로 기한이익상실(EOD) 원칙 및 유예 특례 호출",
            })
            prov_id = f"PROV::{r['article_no']}"
            add_node(prov_id, {
                "id": prov_id, "classLabel": "Provision", "layer": "LEX",
                "label": f"[Provision · {r['article_no']}]\n{r['prov_title'][:28]}...",
                "title": f"v_node_provision · {r['article_no']}",
                "color": "#3b735b", "shape": "box", "matchSec": r["article_no"], "viewName": "v_node_provision",
                "sourceStore": "BigQuery Live (v_node_provision) + Dataplex KC Aspect",
                "record": {"provision_slot_id": r["provision_slot_id"], "article_no": r["article_no"], "title": r["prov_title"], "target_columns": r["target_columns"], "gcs_uri": r["prov_gcs"]},
                "verdictNote": r["prov_title"],
            })
            doc_id = f"DOC::{r['doc_id']}"
            add_node(doc_id, {
                "id": doc_id, "classLabel": "SourceDocument", "layer": "LEX",
                "label": f"[SourceDocument]\n{r['doc_id']}\n({r['authority_level']} · {r['applicable_sector']})",
                "title": f"v_node_source_document · {r['doc_id']}",
                "color": "#477a63", "shape": "box", "matchDocId": r["doc_id"], "viewName": "v_node_source_document",
                "sourceStore": "BigQuery Live (v_node_source_document)",
                "record": {"doc_id": r["doc_id"], "title": r["doc_title"], "authority_level": r["authority_level"], "applicable_sector": r["applicable_sector"]},
                "verdictNote": "내규 조문이 소속된 상위 문서 루트 (PART_OF_DOCUMENT)",
            })
            add_edge(ctx_id, prov_id, f"INVOKES_PROVISION\n[term_key: {r['term_key']}]", "#b88a44", 2.2)
            add_edge(prov_id, doc_id, "PART_OF_DOCUMENT", "#5a8770", 2.0)

            is_deferred = r.get("approval_status") == "APPROVED" and r.get("rehab_priority_claim_yn") == "Y"
            loan_id = f"LOAN::{r['contract_id']}"
            add_node(loan_id, {
                "id": loan_id, "classLabel": "LoanContract", "layer": "ONT",
                "label": f"[LoanContract]\n{r['contract_id']} {r['borrower_name']}\n({r['overdue_days']}일 연체 · 우선변제 {r['rehab_priority_claim_yn']})",
                "title": f"v_node_loan_contract · {r['contract_id']}",
                "color": "#3b735b" if is_deferred else "#a85c56", "shape": "dot", "size": 21, "viewName": "v_node_loan_contract",
                "sourceStore": "Cloud Spanner Federated Live (ont_loan_contracts)",
                "record": {"contract_id": r["contract_id"], "borrower_name": r["borrower_name"], "overdue_days": int(r["overdue_days"] or 0), "asset_classification": r["asset_classification"], "rehab_priority_claim_yn": r["rehab_priority_claim_yn"], "outstanding_amt": int(r["outstanding_amt"] or 0)},
                "verdictNote": "EOD 유예 적법 (내규 제18조 충족)" if is_deferred else "즉시 EOD 예정 통지 대상 (내규 제18조 요건 미달)",
            })
            add_edge(ctx_id, loan_id, "SCOPES_PORTFOLIO", "#6b88a8", 1.8)
            add_edge(loan_id, prov_id, "GOVERNED_BY_CRITERIA", "#b88a44", 1.9)

            if r.get("workout_id"):
                wk_id = f"WK::{r['workout_id']}"
                add_node(wk_id, {
                    "id": wk_id, "classLabel": "WorkoutHistory", "layer": "ONT",
                    "label": f"[WorkoutHistory]\n{r['workout_id']} ({r['consecutive_normal_repay_months']}개월 상환)",
                    "title": f"v_node_workout_history · {r['workout_id']}",
                    "color": "#527a9a", "shape": "dot", "size": 15, "viewName": "v_node_workout_history",
                    "sourceStore": "BigQuery Live (v_node_workout_history)",
                    "record": {"workout_id": r["workout_id"], "contract_id": r["contract_id"], "consecutive_normal_repay_months": int(r["consecutive_normal_repay_months"] or 0), "new_equity_paid_in_krw": int(r["new_equity_paid_in_krw"] or 0), "legal_proceeding_code": r["legal_proceeding_code"]},
                    "verdictNote": f"연속 정상상환 {r['consecutive_normal_repay_months']}개월",
                })
                add_edge(loan_id, wk_id, "HAS_WORKOUT_HISTORY", "#6b88a8", 1.7)
            if r.get("collateral_id"):
                col_id = f"COL::{r['collateral_id']}"
                add_node(col_id, {
                    "id": col_id, "classLabel": "Collateral", "layer": "ONT",
                    "label": f"[Collateral]\n{r['collateral_id']} ({r['guarantee_agency_code']} {r['guarantee_ratio_pct']}%)",
                    "title": f"v_node_collateral · {r['collateral_id']}",
                    "color": "#527a9a", "shape": "dot", "size": 15, "viewName": "v_node_collateral",
                    "sourceStore": "Cloud Spanner Federated Live (ont_collaterals)",
                    "record": {"collateral_id": r["collateral_id"], "contract_id": r["contract_id"], "collateral_type_code": r["collateral_type_code"], "guarantee_agency_code": r["guarantee_agency_code"], "guarantee_ratio_pct": float(r["guarantee_ratio_pct"] or 0)},
                    "verdictNote": f"보증비율 {r['guarantee_ratio_pct']}% (내규 제18조 기준 85%)",
                })
                add_edge(loan_id, col_id, "HAS_COLLATERAL", "#6b88a8", 1.7)
            if r.get("approval_id"):
                ea_id = f"EA::{r['approval_id']}"
                add_node(ea_id, {
                    "id": ea_id, "classLabel": "ExceptionApproval", "layer": "ONT",
                    "label": f"[ExceptionApproval]\n{r['approval_id']} ({r['approval_status']})",
                    "title": f"v_node_exception_approval · {r['approval_id']}",
                    "color": "#3b735b" if r["approval_status"] == "APPROVED" else "#a85c56", "shape": "dot", "size": 15, "viewName": "v_node_exception_approval",
                    "sourceStore": "Cloud Spanner Federated Live (ont_exception_approvals)",
                    "record": {"approval_id": r["approval_id"], "contract_id": r["contract_id"], "approval_type_code": r["approval_type_code"], "approval_status": r["approval_status"], "approver_role_code": r["approver_role_code"], "approval_dt": r["approval_dt"]},
                    "verdictNote": f"본부 여신심사역 결재 상태: {r['approval_status']}",
                })
                add_edge(loan_id, ea_id, "HAS_EXCEPTION_APPROVAL", "#6b88a8", 1.7)
        if "PROV::내규 제16조" in nodes_map and "PROV::내규 제18조" in nodes_map:
            add_edge("PROV::내규 제16조", "PROV::내규 제18조", "HAS_EXCEPTION_PROVISO", "#a85c56", 2.1)

    else:  # CQ12
        sql = f"""
        SELECT
          ctx.context_id, ctx.dept_name,
          inv.term_key, inv.invocation_reason,
          sp.portfolio_scope_rule,
          pr.provision_slot_id, pr.article_no, pr.title AS prov_title, pr.target_columns, pr.gcs_uri AS prov_gcs,
          doc.doc_id, doc.title AS doc_title, doc.authority_level, doc.applicable_sector,
          rc.request_id, rc.contract_id, rc.customer_id, rc.application_reason_code,
          rc.credit_rating_before, rc.credit_rating_after, rc.yoy_revenue_growth_pct,
          rc.review_status_code, rc.approved_cut_bp,
          l.borrower_name, l.product_code, l.applied_rate,
          c.industry_name
        FROM `{PROJECT}.starlight_bank_ontology.v_node_business_context` ctx
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_invokes_provision` inv
          ON ctx.context_id = inv.context_id AND inv.term_key = 'loan-rate'
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_provision` pr
          ON inv.provision_slot_id = pr.provision_slot_id AND pr.article_no IN ('제Ⅱ장 1-나 ④항', '내규 제25조')
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_part_of_document` pod
          ON pr.provision_slot_id = pod.provision_slot_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_source_document` doc
          ON pod.doc_id = doc.doc_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_evaluated_under_provision` ev
          ON pr.provision_slot_id = ev.provision_slot_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_rate_cut_request` rc
          ON ev.request_id = rc.request_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_loan_contract` l
          ON rc.contract_id = l.contract_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_edge_scopes_portfolio` sp
          ON ctx.context_id = sp.context_id AND l.contract_id = sp.contract_id
        JOIN `{PROJECT}.starlight_bank_ontology.v_node_customer` c
          ON rc.customer_id = c.customer_id
        WHERE ctx.context_id = 'BRANCH'
        ORDER BY rc.request_id, pr.article_no
        """
        rows, meta = run_bq_sql(sql)
        for r in rows:
            ctx_id = f"CTX::{r['context_id']}"
            add_node(ctx_id, {
                "id": ctx_id, "classLabel": "BusinessContext", "layer": "ONT",
                "label": f"[BusinessContext]\n{r['context_id']} ({r['dept_name']})",
                "title": f"v_node_business_context · {r['context_id']}",
                "color": "#4a6fa5", "shape": "box", "viewName": "v_node_business_context",
                "sourceStore": "BigQuery Live (v_node_business_context)",
                "record": {"context_id": r["context_id"], "dept_name": r["dept_name"], "term_key": r["term_key"]},
                "verdictNote": f"Glossary term_key='{r['term_key']}'로 금리인하요구권 모범규준 및 내규 제25조 호출",
            })
            prov_id = f"PROV::{r['article_no']}"
            add_node(prov_id, {
                "id": prov_id, "classLabel": "Provision", "layer": "LEX",
                "label": f"[Provision · {r['article_no']}]\n{r['prov_title'][:28]}...",
                "title": f"v_node_provision · {r['article_no']}",
                "color": "#3b735b", "shape": "box", "matchSec": r["article_no"], "viewName": "v_node_provision",
                "sourceStore": "BigQuery Live (v_node_provision) + Dataplex KC Aspect",
                "record": {"provision_slot_id": r["provision_slot_id"], "article_no": r["article_no"], "title": r["prov_title"], "target_columns": r["target_columns"], "gcs_uri": r["prov_gcs"]},
                "verdictNote": r["prov_title"],
            })
            doc_id = f"DOC::{r['doc_id']}"
            add_node(doc_id, {
                "id": doc_id, "classLabel": "SourceDocument", "layer": "LEX",
                "label": f"[SourceDocument]\n{r['doc_id']}\n({r['authority_level']} · {r['applicable_sector']})",
                "title": f"v_node_source_document · {r['doc_id']}",
                "color": "#477a63", "shape": "box", "matchDocId": r["doc_id"], "viewName": "v_node_source_document",
                "sourceStore": "BigQuery Live (v_node_source_document)",
                "record": {"doc_id": r["doc_id"], "title": r["doc_title"], "authority_level": r["authority_level"], "applicable_sector": r["applicable_sector"]},
                "verdictNote": "조문이 소속된 상위 문서 루트 (PART_OF_DOCUMENT)",
            })
            add_edge(ctx_id, prov_id, f"INVOKES_PROVISION\n[term_key: {r['term_key']}]", "#b88a44", 2.2)
            add_edge(prov_id, doc_id, "PART_OF_DOCUMENT", "#5a8770", 2.0)

            cust_id = f"CUST::{r['customer_id']}"
            add_node(cust_id, {
                "id": cust_id, "classLabel": "Customer", "layer": "ONT",
                "label": f"[Customer]\n{r['customer_id']} {r['borrower_name']}\n({r['credit_rating_before']} → {r['credit_rating_after']})",
                "title": f"v_node_customer · {r['customer_id']}",
                "color": "#527a9a", "shape": "dot", "size": 17, "viewName": "v_node_customer",
                "sourceStore": "BigQuery Live (v_node_customer + ont_entity_aliases)",
                "record": {"customer_id": r["customer_id"], "borrower_name": r["borrower_name"], "industry_name": r["industry_name"], "credit_rating_change": f"{r['credit_rating_before']} -> {r['credit_rating_after']}"},
                "verdictNote": f"신용등급 변동: {r['credit_rating_before']} → {r['credit_rating_after']}",
            })
            loan_id = f"LOAN::{r['contract_id']}"
            add_node(loan_id, {
                "id": loan_id, "classLabel": "LoanContract", "layer": "ONT",
                "label": f"[LoanContract]\n{r['contract_id']} ({r['borrower_name']})",
                "title": f"v_node_loan_contract · {r['contract_id']}",
                "color": "#3b6ea5", "shape": "dot", "size": 19, "viewName": "v_node_loan_contract",
                "sourceStore": "Cloud Spanner Federated Live (ont_loan_contracts)",
                "record": {"contract_id": r["contract_id"], "customer_id": r["customer_id"], "borrower_name": r["borrower_name"], "product_code": r["product_code"], "applied_rate": float(r["applied_rate"] or 0)},
                "verdictNote": "여신계약 원장 허브",
            })
            is_app = r["review_status_code"] == "APPROVED"
            rc_id = f"RC::{r['request_id']}"
            add_node(rc_id, {
                "id": rc_id, "classLabel": "RateCutRequest", "layer": "ONT",
                "label": f"[RateCutRequest · {r['review_status_code']}]\n{r['request_id']} ({r['credit_rating_before']}→{r['credit_rating_after']} · -{r['approved_cut_bp']}bp)",
                "title": f"v_node_rate_cut_request · {r['request_id']}",
                "color": "#3b735b" if is_app else "#a85c56", "shape": "dot", "size": 21, "viewName": "v_node_rate_cut_request",
                "sourceStore": "Cloud Spanner Federated Live (ont_rate_cut_requests)",
                "record": {"request_id": r["request_id"], "contract_id": r["contract_id"], "borrower_name": r["borrower_name"], "application_reason_code": r["application_reason_code"], "credit_rating_before": r["credit_rating_before"], "credit_rating_after": r["credit_rating_after"], "yoy_revenue_growth_pct": float(r["yoy_revenue_growth_pct"] or 0), "review_status_code": r["review_status_code"], "approved_cut_bp": int(r["approved_cut_bp"] or 0)},
                "verdictNote": f"심사 결과: {r['review_status_code']} ({r['approved_cut_bp']}bp 인하)",
            })
            add_edge(ctx_id, loan_id, "SCOPES_PORTFOLIO", "#6b88a8", 1.8)
            add_edge(loan_id, cust_id, "BORROWED_BY", "#6b88a8", 1.7)
            add_edge(loan_id, rc_id, "HAS_RATE_CUT_REQUEST", "#6b88a8", 1.9)
            add_edge(rc_id, prov_id, "EVALUATED_UNDER_PROVISION", "#b88a44", 2.0)
        if "PROV::제Ⅱ장 1-나 ④항" in nodes_map and "PROV::내규 제25조" in nodes_map:
            add_edge("PROV::제Ⅱ장 1-나 ④항", "PROV::내규 제25조", "DELEGATES_TO_INTERNAL", "#5a8770", 2.1)

    try:
        resolved_obj_map, obj_bq_meta = obj_future.result(timeout=25)
    except Exception:
        traceback.print_exc()
        resolved_obj_map, obj_bq_meta = {}, {}
    finally:
        obj_executor.shutdown(wait=False)

    # Check if user edited GQL and introduced additional Provision or SourceDocument nodes
    extra_provs = []
    extra_docs = []
    for n in nodes_map.values():
        rec = n.get("record") or {}
        if n.get("classLabel") == "Provision" and rec.get("provision_slot_id"):
            slot_id = rec["provision_slot_id"]
            if f"PROVISION::{slot_id}" not in resolved_obj_map:
                extra_provs.append(slot_id)
        elif n.get("classLabel") == "SourceDocument" and rec.get("doc_id"):
            did = rec["doc_id"]
            if f"DOC::{did}" not in resolved_obj_map:
                extra_docs.append(did)
    if extra_provs or extra_docs:
        try:
            extra_map, _ = resolve_bq_objectrefs_live(extra_provs, extra_docs)
            resolved_obj_map.update(extra_map)
        except Exception:
            traceback.print_exc()

    # Attach live ObjectRef metadata & GCS Markdown to every Provision / SourceDocument node
    for n in nodes_map.values():
        rec = n.get("record") or {}
        if n.get("classLabel") == "Provision" and rec.get("provision_slot_id"):
            slot_id = rec["provision_slot_id"]
            obj_entry = resolved_obj_map.get(f"PROVISION::{slot_id}")
            if obj_entry:
                rec["gcs_obj_ref"] = obj_entry["gcs_obj_ref"]
                n["objectRefLive"] = obj_entry["objectRefLive"]
                n["sourceStore"] = "BigQuery Live (v_node_provision · ObjectRef -> GCS Signed Read) + Dataplex KC"
        elif n.get("classLabel") == "SourceDocument" and rec.get("doc_id"):
            did = rec["doc_id"]
            obj_entry = resolved_obj_map.get(f"DOC::{did}")
            if obj_entry:
                rec["gcs_obj_ref"] = obj_entry["gcs_obj_ref"]
                n["objectRefLive"] = obj_entry["objectRefLive"]
                n["sourceStore"] = "BigQuery Live (v_node_source_document · ObjectRef -> GCS Signed Read)"

    meta["spanner_data_boost"] = True
    meta["spanner_external_dataset"] = "starlight_bank_ext (Cloud Spanner Data Boost Federated)"
    meta["objectref_connection"] = "us-central1.okf-gcs-conn"
    meta["objectref_job_id"] = obj_bq_meta.get("job_id", "")
    meta["objectref_resolved_count"] = len(resolved_obj_map)

    return {
        "ok": True,
        "mode": mode,
        "job_id": meta.get("job_id", "bqjob_live"),
        "elapsed_ms": meta.get("elapsed_ms", 0),
        "row_count": meta.get("row_count", len(rows)),
        "meta": meta,
        "nodes": list(nodes_map.values()),
        "edges": edges_list,
        "raw_rows": rows[:25],
    }


_ALLOWED_STATIC_PREFIXES = (
    "/okf_veri_web/",
    "/hands-on/",
    "/finance/okf/",
    "/finance/data/un_data/",
    "/ecommerce/okf/",
    "/ecommerce/data/un_data/",
    "/okf/",
    "/data/un_data/",
    "/docs/",
    "/favicon.ico",
)


class StudioRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def translate_path(self, path: str) -> str:
        parsed_path = urlparse(path).path
        if parsed_path.startswith("/okf/"):
            path = "/finance" + path
        elif parsed_path.startswith("/data/un_data/"):
            path = "/finance" + path
        return super().translate_path(path)

    def end_headers(self):
        try:
            parsed_path = urlparse(getattr(self, "path", "")).path
            if parsed_path == "/okf_veri_web/index.html":
                pragma = (self.headers.get("Pragma") or "").lower()
                cc = (self.headers.get("Cache-Control") or "").lower()
                is_hard = ("no-cache" in pragma) or ("no-cache" in cc)
                self.send_header(
                    "Set-Cookie",
                    f"okf_hard_reload={'1' if is_hard else '0'}; Path=/; SameSite=Lax",
                )
        except Exception:
            pass
        super().end_headers()

    def _send_json(self, code: int, payload: dict):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def list_directory(self, path):
        self.send_error(403, "Directory listing is disabled")
        return None

    def _is_allowed_static_path(self, raw_path: str) -> bool:
        norm = os.path.normpath(raw_path)
        if not norm.startswith("/"):
            return False
        if norm in ("/okf_veri_web", "/docs", "/hands-on"):
            norm = norm + "/"
        return any(norm.startswith(prefix) for prefix in _ALLOWED_STATIC_PREFIXES)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_HEAD(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html", "/okf_veri_web"):
            target = "/okf_veri_web/index.html"
            if parsed.query:
                target = f"{target}?{parsed.query}"
            self.send_response(302)
            self.send_header("Location", target)
            self.end_headers()
            return
        if parsed.path in ("/hands-on", "/hands-on/"):
            self.send_response(302)
            self.send_header("Location", "/hands-on/index.html")
            self.end_headers()
            return
        if not self._is_allowed_static_path(parsed.path):
            self.send_error(404, "Not Found")
            return
        super().do_HEAD()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/api/health", "/healthz"):
            self._send_json(
                200,
                {
                    "ok": True,
                    "service": os.environ.get("K_SERVICE", "krda-ontology-studio"),
                    "agent_mode": os.environ.get("STARLIGHT_AGENT_MODE", "local"),
                    "allow_publish": ALLOW_PUBLISH,
                },
            )
            return
        if parsed.path in ("/", "/index.html", "/okf_veri_web"):
            target = "/okf_veri_web/index.html"
            if parsed.query:
                target = f"{target}?{parsed.query}"
            self.send_response(302)
            self.send_header("Location", target)
            self.end_headers()
            return
        if parsed.path in ("/hands-on", "/hands-on/"):
            self.send_response(302)
            self.send_header("Location", "/hands-on/index.html")
            self.end_headers()
            return
        if parsed.path == "/api/okf/state":
            st = load_state()
            self._send_json(200, {"ok": True, "state": st})
            return
        if parsed.path == "/api/agent/questions":
            try:
                from agent_chat_engine import get_agent_questions
                self._send_json(200, {"ok": True, "questions": get_agent_questions()})
                return
            except Exception as e:
                traceback.print_exc()
                self._send_json(500, {"ok": False, "error": str(e)})
                return
        if not self._is_allowed_static_path(parsed.path):
            self.send_error(404, "Not Found")
            return
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path in ("/api/agent/chat", "/api/agent/chat/stream"):
            try:
                from agent_chat_engine import execute_agent_chat, execute_kmarket_agent_chat
                length = int(self.headers.get("Content-Length", "0"))
                body_bytes = self.rfile.read(length) if length > 0 else b"{}"
                data = json.loads(body_bytes.decode("utf-8"))
                is_ecom = data.get("project") == "ecommerce-ontology"
                use_stream = parsed.path.endswith("/stream") or bool(data.get("stream"))
                if use_stream:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                    self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                    self.send_header("X-Accel-Buffering", "no")
                    self.end_headers()

                    def _send_stage(msg: str) -> None:
                        line = json.dumps({"type": "stage", "text": msg}, ensure_ascii=False) + "\n"
                        self.wfile.write(line.encode("utf-8"))
                        self.wfile.flush()

                    # Same I/O as Agent Runtime: engine defaults to app.orchestrator.bq_io (ADR 0007).
                    try:
                        if is_ecom:
                            res = execute_kmarket_agent_chat(
                                data, run_bq_sql, resolve_bq_objectrefs_live, on_stage=_send_stage
                            )
                        else:
                            res = execute_agent_chat(data, on_stage=_send_stage)
                    except Exception as inner_e:
                        traceback.print_exc()
                        res = {"ok": False, "error": str(inner_e)}
                    final_line = json.dumps({"type": "result", "data": res}, ensure_ascii=False, default=str) + "\n"
                    self.wfile.write(final_line.encode("utf-8"))
                    self.wfile.flush()
                    return

                if is_ecom:
                    res = execute_kmarket_agent_chat(data, run_bq_sql, resolve_bq_objectrefs_live)
                else:
                    res = execute_agent_chat(data)
                self._send_json(200, res)
                return
            except Exception as e:
                traceback.print_exc()
                self._send_json(500, {"ok": False, "error": str(e)})
                return

        if parsed.path in ("/api/rag/chat", "/api/rag/chat/stream"):
            try:
                from rag_remote_client import execute_kmarket_rag_chat, execute_rag_chat
                from ecommerce_agent_handler import execute_ecommerce_rag_chat
                length = int(self.headers.get("Content-Length", "0"))
                body_bytes = self.rfile.read(length) if length > 0 else b"{}"
                data = json.loads(body_bytes.decode("utf-8"))
                is_ecom = data.get("project") == "ecommerce-ontology"
                kmarket_rag_meta = os.path.join(ROOT, "ecommerce", "agents", "kmarket-rag-agent", "deployment_metadata.json")
                explicit_mode = os.environ.get("STARLIGHT_AGENT_MODE", "").strip().lower()
                use_remote_ecom_rag = (explicit_mode == "remote") or (
                    explicit_mode != "local"
                    and (bool(os.environ.get("KMARKET_RAG_AGENT_RESOURCE")) or os.path.exists(kmarket_rag_meta))
                )
                use_stream = parsed.path.endswith("/stream") or bool(data.get("stream"))
                if use_stream:
                    self.send_response(200)
                    self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                    self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
                    self.send_header("X-Accel-Buffering", "no")
                    self.end_headers()

                    def _send_rag_stage(msg: str) -> None:
                        line = json.dumps({"type": "stage", "text": msg}, ensure_ascii=False) + "\n"
                        self.wfile.write(line.encode("utf-8"))
                        self.wfile.flush()

                    try:
                        if is_ecom:
                            if use_remote_ecom_rag:
                                res = execute_kmarket_rag_chat(data, on_stage=_send_rag_stage)
                            else:
                                res = execute_ecommerce_rag_chat(data, run_bq_sql, on_stage=_send_rag_stage)
                        else:
                            res = execute_rag_chat(data, on_stage=_send_rag_stage)
                    except Exception as inner_e:
                        traceback.print_exc()
                        res = {"ok": False, "error": str(inner_e)}
                    final_line = json.dumps({"type": "result", "data": res}, ensure_ascii=False, default=str) + "\n"
                    self.wfile.write(final_line.encode("utf-8"))
                    self.wfile.flush()
                    return

                if is_ecom:
                    if use_remote_ecom_rag:
                        res = execute_kmarket_rag_chat(data)
                    else:
                        res = execute_ecommerce_rag_chat(data, run_bq_sql)
                else:
                    res = execute_rag_chat(data)
                self._send_json(200, res)
                return
            except Exception as e:
                traceback.print_exc()
                self._send_json(500, {"ok": False, "error": str(e)})
                return

        if parsed.path == "/api/bq-graph/query":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body_bytes = self.rfile.read(length) if length > 0 else b"{}"
                data = json.loads(body_bytes.decode("utf-8"))
                res = execute_live_bq_graph_query(data)
                self._send_json(200, res)
                return
            except Exception as e:
                traceback.print_exc()
                self._send_json(500, {"ok": False, "error": str(e)})
                return

        if parsed.path in ("/api/okf/publish", "/api/okf/batch_publish"):
            if not ALLOW_PUBLISH:
                self._send_json(
                    403,
                    {
                        "ok": False,
                        "error": "Publish is disabled (STARLIGHT_ALLOW_PUBLISH=false).",
                    },
                )
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body_bytes = self.rfile.read(length)
                data = json.loads(body_bytes.decode("utf-8"))
                st = load_state()

                if parsed.path == "/api/okf/publish":
                    res = process_single_publish(data, st)
                    save_state(st)
                    self._send_json(200, {"ok": True, "result": res, "state": st})
                    return

                if parsed.path == "/api/okf/batch_publish":
                    items = data.get("items", [])
                    results = []
                    for it in items:
                        results.append(process_single_publish(it, st))
                    save_state(st)
                    self._send_json(
                        200,
                        {
                            "ok": True,
                            "count": len(results),
                            "results": results,
                            "state": st,
                        },
                    )
                    return
            except Exception as e:
                traceback.print_exc()
                self._send_json(500, {"ok": False, "error": str(e)})
                return

        self._send_json(404, {"ok": False, "error": "Unknown endpoint"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8090"))
    server = ThreadingHTTPServer(("0.0.0.0", port), StudioRequestHandler)
    print(f"[StudioServer] Listening on http://0.0.0.0:{port} (ROOT={ROOT} · Static + Real GCP GCS/Dataplex/BigQuery API)")
    server.serve_forever()

