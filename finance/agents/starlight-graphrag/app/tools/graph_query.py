"""graph_query — Unified GQL Planner & Executor (with BigQuery dry-run validation)."""

from __future__ import annotations

from typing import Any

from google.adk.tools import ToolContext

from app.runtime import get_runtime
from app.services import gql_composer


_OKF_PATH_PREFIXES = (
    "regulations/",
    "internal_policies/",
    "research_briefs/",
    "distractors/",
    "versions/",
)


def _extract_touched(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    slot_ids: list[str] = []
    kc_ids: list[str] = []
    contract_ids: set[str] = set()
    customer_ids: set[str] = set()
    for r in rows:
        for k, v in r.items():
            if not v or not isinstance(v, str):
                continue
            kl = k.lower()
            is_okf_path = v.startswith(_OKF_PATH_PREFIXES)
            if (
                "provision_slot_id" in kl
                or "kc_entry_id" in kl
                or "kc_id" in kl
                or is_okf_path
                or v.startswith("art_")
                or v.startswith("tbl3_")
            ):
                if v not in slot_ids:
                    slot_ids.append(v)
            if (
                "kc_entry_id" in kl
                or "kc_id" in kl
                or "provision_slot_id" in kl
                or is_okf_path
                or v.startswith("okf-")
            ):
                if v not in kc_ids:
                    kc_ids.append(v)
            if "contract_id" in kl or v.startswith("LN_"):
                contract_ids.add(v)
            if "customer_id" in kl or v.startswith("CUST_"):
                customer_ids.add(v)
    return {
        "provision_slot_id": slot_ids,
        "kc_entry_id": kc_ids,
        "contract_id": sorted(contract_ids),
        "customer_id": sorted(customer_ids),
    }


def graph_query(gql: str, tool_context: ToolContext) -> dict[str, Any]:
    """Validate (Static Lint + BigQuery Dry-Run) and execute a unified GQL query on `finance_graph`.

    Because `starlight_bank_ontology.finance_graph` integrates all 11 node classes (including
    Spanner federated `LoanContract`, `DelinquencyEvent`, `Collateral`, `RateCutRequest`,
    `ExceptionApproval`, plus `Customer`, `FinancialProduct`, `WorkoutHistory`, `BusinessContext`,
    `Provision`, `SourceDocument`) and 15 edge views (`SCOPES_PORTFOLIO`, `INVOKES_PROVISION`,
    `GOVERNED_BY_CRITERIA`, etc.), both multi-hop regulatory traversal AND quantitative ledger
    calculations/aggregations are performed in a single unified GQL query:
      - `GRAPH starlight_bank_ontology.finance_graph MATCH ... RETURN ...`
      - or `SELECT ... FROM GRAPH_TABLE(starlight_bank_ontology.finance_graph MATCH ... COLUMNS (...))`

    Before execution, `gql_composer.validate` runs static schema checks and BigQuery
    `QueryJobConfig(dry_run=True)` verification.

    Args:
        gql: Unified GQL statement anchored on the KC `gql_match_template` snippets.

    Returns:
        {"status": "ok", "dry_run_bytes": int, "rows": [...], "touched": {"provision_slot_id": [...], "kc_entry_id": [...]}}
        or {"status": "invalid", "errors": [...], "hints": [...]} when static or dry-run validation fails.
    """
    rt = get_runtime()
    card = rt.get_schema_card()
    val = gql_composer.validate(
        gql,
        card,
        graph_fqn=rt.settings.graph_fqn,
        max_hops=rt.settings.max_graph_hops,
        max_edge_patterns=rt.settings.max_edge_patterns,
        max_rows=rt.settings.max_rows,
        max_bytes_billed=rt.settings.max_bytes_billed,
        graph_port=rt.graph_port,
    )
    if not val.ok:
        return {
            "status": "invalid",
            "gql": val.gql,
            "dry_run_bytes": val.dry_run_bytes,
            "errors": list(val.errors),
            "hints": list(val.hints),
        }

    exec_res = rt.graph_port.run_gql(val.gql, max_rows=rt.settings.max_rows)
    rows = exec_res.get("rows") or []
    return {
        "status": "ok",
        "gql": val.gql,
        "dry_run_bytes": val.dry_run_bytes,
        "bytes_processed": exec_res.get("bytes_processed", val.dry_run_bytes),
        "job_id": exec_res.get("job_id"),
        "row_count": len(rows),
        "rows": rows,
        "touched": _extract_touched(rows),
    }
