# -*- coding: utf-8 -*-
"""K-Market 3-Layer Ontology Graph Agent (Google ADK Implementation).

Implements:
  - Step 0 (`before_agent_callback`): Entity Alias Anchoring from `kmarket_ontology.ont_entity_aliases`
  - Step 1 (`execute_kmarket_gql`): BigQuery Property Graph GQL execution with `dry_run=True` & syntax self-repair
  - Step 2 (`fetch_kmarket_provisions`): Verbatim Korean regulation/policy lookup from `kmarket_ontology.lex_provisions`
"""

from __future__ import annotations

import os
import re
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.cloud import bigquery
from google.genai import types

from .prompts import KMARKET_SYSTEM_INSTRUCTION

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "YOUR_PROJECT_ID")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL = os.environ.get("KMARKET_MODEL", "gemini-2.5-flash")

_bq_client: bigquery.Client | None = None
_alias_cache: list[dict[str, str]] | None = None


def get_bq_client() -> bigquery.Client:
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=PROJECT_ID, location=LOCATION)
    return _bq_client


def _load_aliases() -> list[dict[str, str]]:
    global _alias_cache
    if _alias_cache is not None:
        return _alias_cache
    try:
        client = get_bq_client()
        sql = f"""
        SELECT alias_text, canonical_id, entity_class, alias_group
        FROM `{PROJECT_ID}.kmarket_ontology.ont_entity_aliases`
        ORDER BY LENGTH(alias_text) DESC
        """
        _alias_cache = [dict(r) for r in client.query(sql).result()]
    except Exception:
        _alias_cache = []
    return _alias_cache


# ============================================================================
# Step 0: Entity Alias Anchoring Callback (`before_agent_callback`)
# ============================================================================
def anchor_kmarket_entities_callback(callback_context: CallbackContext) -> types.Content | None:
    """Extracts canonical IDs from the user's natural-language question before LLM reasoning."""
    user_text = ""
    if callback_context.user_content and callback_context.user_content.parts:
        user_text = " ".join(
            p.text for p in callback_context.user_content.parts if getattr(p, "text", None)
        )
    if not user_text:
        return None

    matched: list[str] = []
    seen_cids: set[str] = set()
    for row in _load_aliases():
        alias = row["alias_text"]
        cid = row["canonical_id"]
        if alias in user_text and cid not in seen_cids:
            seen_cids.add(cid)
            matched.append(f"- '{alias}' ➔ `{cid}` ({row['entity_class']} / {row['alias_group']})")

    if matched:
        callback_context.state["anchored_entities"] = "\n".join(matched[:15])
    else:
        callback_context.state["anchored_entities"] = "(자동 매칭된 엔티티 별칭 없음)"
    return None


# ============================================================================
# Step 1: BigQuery Property Graph GQL Tool (with Dry-Run & Auto-Repair)
# ============================================================================
def _auto_repair_gql(gql: str, error_msg: str = "") -> str:
    """Applies deterministic syntax fixes for common BigQuery GQL mistakes."""
    repaired = gql.strip()
    # 1. Ensure Order label is backticked (`Order`)
    repaired = re.sub(r":\s*Order\b(?!`)", ":`Order`", repaired)
    # 2. Replace placeholder project ID if present
    for placeholder in ("YOUR_PROJECT_ID", "finance-ontology-changseop", "partner-caa-project-0827"):
        if placeholder != PROJECT_ID:
            repaired = repaired.replace(placeholder, PROJECT_ID)
    return repaired


def execute_kmarket_gql(gql_query: str) -> dict[str, Any]:
    """Executes a BigQuery GQL query against `kmarket_ontology.ecommerce_graph` with dry-run validation.

    Args:
        gql_query: Full GQL query starting with `GRAPH `PROJECT_ID.kmarket_ontology.ecommerce_graph` MATCH ...`

    Returns:
        Dictionary containing `status`, `executed_gql`, `row_count`, and `rows` (or `error` for self-repair).
    """
    client = get_bq_client()
    candidate_gql = _auto_repair_gql(gql_query)

    # Step 1a: Pre-execution Dry-Run Gate
    try:
        dry_cfg = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        client.query(candidate_gql, job_config=dry_cfg)
    except Exception as dry_err:
        return {
            "status": "DRY_RUN_ERROR",
            "failed_gql": candidate_gql,
            "error": str(dry_err)[:600],
            "repair_hint": (
                "GQL 문법 오류가 발생했습니다. 1) `Order` 라벨을 백틱(`Order`)으로 감쌌는지, "
                "2) RETURN 절에 스칼라 프로퍼티(예: oi.order_item_id)만 반환했는지, "
                "3) 스키마에 존재하는 엣지/프로퍼티명인지 확인하여 수정 후 다시 호출하세요."
            ),
        }

    # Step 1b: Live Execution
    try:
        rows = [dict(r) for r in client.query(candidate_gql).result()]
        return {
            "status": "SUCCESS",
            "executed_gql": candidate_gql,
            "row_count": len(rows),
            "rows": rows[:50],
        }
    except Exception as exec_err:
        return {
            "status": "EXECUTION_ERROR",
            "failed_gql": candidate_gql,
            "error": str(exec_err)[:600],
        }


# ============================================================================
# Step 2: Provision Verbatim Text Lookup Tool
# ============================================================================
def fetch_kmarket_provisions(provision_slot_ids: list[str]) -> dict[str, Any]:
    """Fetches full Korean regulatory & internal policy text for matched `provision_slot_id`s.

    Args:
        provision_slot_ids: List of `provision_slot_id` strings discovered via GQL traversal.

    Returns:
        Dictionary containing `provisions` with `article_no`, `title`, `provision_role`,
        `missing_schema_columns`, and verbatim `full_text`.
    """
    if not provision_slot_ids:
        return {"status": "EMPTY", "provisions": []}

    client = get_bq_client()
    sql = f"""
    SELECT
      p.provision_slot_id,
      p.doc_id,
      d.title AS document_title,
      d.authority_level,
      d.applicable_sector,
      p.article_no,
      p.title,
      p.provision_role,
      p.target_columns,
      p.missing_schema_columns,
      p.full_text
    FROM `{PROJECT_ID}.kmarket_ontology.lex_provisions` p
    LEFT JOIN `{PROJECT_ID}.kmarket_ontology.lex_source_documents` d
      ON p.doc_id = d.doc_id
    WHERE p.provision_slot_id IN UNNEST(@slot_ids)
    ORDER BY p.provision_slot_id
    """
    job_cfg = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ArrayQueryParameter("slot_ids", "STRING", list(provision_slot_ids))]
    )
    rows = [dict(r) for r in client.query(sql, job_config=job_cfg).result()]
    return {
        "status": "SUCCESS",
        "count": len(rows),
        "provisions": rows,
    }


root_agent = LlmAgent(
    name="kmarket_graph_agent",
    model=MODEL,
    description="K마켙(K-Market) 3-Layer 이커머스 온톨로지 및 BigQuery Property Graph 기반 의사결정 에이전트",
    instruction=KMARKET_SYSTEM_INSTRUCTION.format(project_id=PROJECT_ID)
    + "\n\n# [Step 0 자동 바인딩된 엔티티 앵커]\n{anchored_entities?}",
    before_agent_callback=anchor_kmarket_entities_callback,
    tools=[execute_kmarket_gql, fetch_kmarket_provisions],
)
