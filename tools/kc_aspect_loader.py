#!/usr/bin/env python3
"""ADK Agent Runtime Helper for Dataplex Knowledge Catalog Aspect Loading,
Longest-Match-First Entity/Glossary Alias Resolution, and KC-Only Provision
Lifecycle & Superseded-Chain Verification.

Usage:
  python3 tools/kc_aspect_loader.py
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from google.cloud import bigquery

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"

PROJECT = "finance-ontology-changseop"
PROJECT_NUMBER = "567090080191"
LOCATION = "us-central1"
ONT_DS = "starlight_bank_ontology"
GRAPH_NAME = "finance_graph"
ENTRY_GROUP = "finance-okf"
ANCHOR_ASPECT_KEY = f"{PROJECT_NUMBER}.{LOCATION}.ontology-class-anchors"
OKF_ASPECT_KEY = f"{PROJECT_NUMBER}.{LOCATION}.okf"


def get_gcloud_token() -> str:
    return subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True, timeout=10
    ).strip()


def load_graph_anchor_aspect(token: str | None = None) -> dict:
    """Fetches the `ontology-class-anchors` Custom Aspect attached to the
    `starlight_bank_ontology.finance_graph` entry in Dataplex Knowledge Catalog.
    """
    tok = token or get_gcloud_token()
    entry_path = (
        f"projects/{PROJECT}/locations/{LOCATION}/entryGroups/@bigquery/entries/"
        f"bigquery.googleapis.com/projects/{PROJECT}/datasets/{ONT_DS}/propertyGraphs/{GRAPH_NAME}"
    )
    url = f"https://dataplex.googleapis.com/v1/{entry_path}?view=CUSTOM&aspectTypes=projects/{PROJECT}/locations/{LOCATION}/aspectTypes/ontology-class-anchors"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        entry_json = json.loads(resp.read().decode("utf-8"))
    aspect = entry_json.get("aspects", {}).get(ANCHOR_ASPECT_KEY, {}).get("data", {})
    return aspect


def resolve_query_aliases_longest_match(
    user_query: str,
    alias_rows: list[dict],
) -> list[dict]:
    """Resolves entity and glossary aliases in `user_query` using Longest-Match-First
    non-overlapping character span matching.

    Prevents short prefixes (e.g., '별빛') from falsely matching multiple entities when
    a longer specific span (e.g., '별빛정밀', '별빛 프라임 중견기업 운전자금') is present.
    """
    # Sort aliases by length descending so longest spans match first
    sorted_rows = sorted(
        alias_rows,
        key=lambda r: len(r["alias_term"]),
        reverse=True,
    )
    occupied_spans: list[tuple[int, int]] = []
    matched: list[dict] = []

    for row in sorted_rows:
        term = row["alias_term"]
        if len(term) < 2:
            continue
        start_idx = user_query.find(term)
        if start_idx == -1:
            continue
        end_idx = start_idx + len(term)
        # Check overlap with already occupied spans
        overlaps = any(not (end_idx <= s or start_idx >= e) for s, e in occupied_spans)
        if overlaps:
            continue
        occupied_spans.append((start_idx, end_idx))
        matched.append({
            "span": (start_idx, end_idx),
            "alias_term": term,
            "target_class": row["target_class"],
            "match_bind_key": row["match_bind_key"],
            "canonical_id": row["canonical_id"],
            "canonical_display": row["canonical_display"],
            "gql_match_snippet": row["gql_match_snippet"],
        })

    matched.sort(key=lambda m: m["span"][0])
    return matched


def resolve_kc_provision(
    kc_entry_id: str,
    token: str | None = None,
    max_depth: int = 3,
) -> dict:
    """Single Source of Governance verification in Dataplex Knowledge Catalog:
    - Looks up `kc_entry_id` in `finance-okf` entry group.
    - If `status == 'verified'`, returns `ALLOW`.
    - If `status == 'deprecated'`, follows `superseded_by` inside KC `okf` Aspect (`extra` JSON)
      up to `max_depth` hops until a `verified` replacement entry is found (`SUPERSEDED_RESOLVED`).
    - If no `verified` replacement exists, returns `BLOCKED_DEPRECATED`.
    """
    tok = token or get_gcloud_token()
    visited: list[str] = []
    curr_id = kc_entry_id

    for depth in range(max_depth + 1):
        visited.append(curr_id)
        entry_url = (
            f"https://dataplex.googleapis.com/v1/projects/{PROJECT}/locations/{LOCATION}"
            f"/entryGroups/{ENTRY_GROUP}/entries/{curr_id}?view=ALL"
        )
        req = urllib.request.Request(entry_url, headers={"Authorization": f"Bearer {tok}"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                entry = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {
                "verdict": "BLOCKED_NOT_FOUND",
                "requested_entry_id": kc_entry_id,
                "failed_at": curr_id,
                "http_status": e.code,
                "chain": visited,
            }

        okf_data = entry.get("aspects", {}).get(OKF_ASPECT_KEY, {}).get("data", {})
        status = okf_data.get("status", "unknown")
        version = okf_data.get("version", "0.2.0")
        verified_events = okf_data.get("verified", [])
        gcs_uri = entry.get("entrySource", {}).get("resource", "")

        if status in ("verified", "stable") and status != "deprecated":
            return {
                "verdict": "ALLOW" if depth == 0 else "SUPERSEDED_RESOLVED",
                "requested_entry_id": kc_entry_id,
                "active_entry_id": curr_id,
                "status": status,
                "version": version,
                "verified_count": len(verified_events),
                "gcs_uri": gcs_uri,
                "hops": depth,
                "chain": visited,
            }

        # If deprecated, inspect `extra` JSON or `superseded_by` in KC okf Aspect
        next_id = ""
        extra_raw = okf_data.get("extra", "")
        if extra_raw:
            try:
                extra_obj = json.loads(extra_raw) if isinstance(extra_raw, str) and extra_raw.startswith("{") else {}
                next_id = str(extra_obj.get("superseded_by", "")).strip()
            except Exception:
                pass
        if not next_id:
            next_id = str(okf_data.get("superseded_by", "")).strip()
        # Strip optional version suffix like ` (v0.3.0)`
        if " (" in next_id:
            next_id = next_id.split(" (", 1)[0].strip()

        if not next_id or next_id in visited:
            return {
                "verdict": "BLOCKED_DEPRECATED",
                "requested_entry_id": kc_entry_id,
                "blocked_at": curr_id,
                "status": status,
                "version": version,
                "reason": f"KC Entry `{curr_id}` is `{status}` with no valid `superseded_by` target.",
                "chain": visited,
            }
        curr_id = next_id

    return {
        "verdict": "BLOCKED_MAX_DEPTH_EXCEEDED",
        "requested_entry_id": kc_entry_id,
        "chain": visited,
    }


def main() -> None:
    token = get_gcloud_token()
    aspect = load_graph_anchor_aspect(token)
    print("=== 1. Loaded `ontology-class-anchors` Aspect from Dataplex KC (`finance_graph`) ===")
    print(f"Graph ID        : {aspect.get('graph_id')}")
    print(f"Ontology Version: {aspect.get('ontology_version')}")
    print(f"Alias Table FQN : {aspect.get('alias_table_fqn')}")
    print(f"KC Glossary     : {aspect.get('kc_glossary_resource')}")
    print(f"Class Anchors   : {len(aspect.get('class_anchors', []))} classes")
    for ca in aspect.get("class_anchors", []):
        print(f"  - [{ca['layer']}] {ca['class_label']} (PK={ca['primary_key']}, Anchor={ca['anchor_type']}) -> {ca['gql_match_template']}")

    client = bigquery.Client(project=PROJECT, location=LOCATION)
    alias_rows = [
        dict(r)
        for r in client.query(f"SELECT * FROM `{PROJECT}.{ONT_DS}.ont_entity_aliases`").result()
    ]

    sample_queries = [
        "여신관리팀 조기경보 기준으로 연체율 산출해줘",
        "에이펙스세미콘이 보유한 별빛 프라임 중견기업 운전자금의 기한이익상실 유예 적격성 심사해줘",
        "태성금속과 극동철강의 채권재조정 별표3 라목 특례 충족 여부 비교해줘",
    ]
    print("\n=== 2. Longest-Match-First Entity & Glossary Alias Resolution Test ===")
    for q in sample_queries:
        matches = resolve_query_aliases_longest_match(q, alias_rows)
        print(f"\nQuery: \"{q}\"")
        for m in matches:
            print(f"  * '{m['alias_term']}' -> [{m['target_class']}] {m['canonical_id']} ({m['canonical_display']}) => {m['gql_match_snippet']}")

    print("\n=== 3. KC-Only Provision Governance Verification Test ===")
    res_verified = resolve_kc_provision(
        "regulations/01_fsc_banking_reg/ch06_prudential_management_and_provisioning/art_029",
        token=token,
    )
    print("Verified Entry Check:", json.dumps(res_verified, ensure_ascii=False))


if __name__ == "__main__":
    main()
