"""before_tool guards. Returning a dict short-circuits the tool with that response."""

from __future__ import annotations

from typing import Any

from google.adk.tools import BaseTool, ToolContext

from app.domain import state_keys as sk
from app.runtime import get_runtime
from app.services import gql_composer


def _tool_name(tool: BaseTool | Any) -> str:
    return str(getattr(tool, "name", None) or getattr(tool, "__name__", "") or "")


def tool_budget(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> dict | None:
    """Increment temp:tool_calls_used; over budget → {"status": "budget_exhausted", ...}."""
    state: Any = getattr(tool_context, "state", None)
    if state is None:
        return None
    rt = get_runtime()
    used = int(state.get(sk.TOOL_CALLS_USED) or 0) + 1
    state[sk.TOOL_CALLS_USED] = used
    if used > rt.settings.tool_budget:
        return {
            "status": "budget_exhausted",
            "tool_calls_used": used,
            "tool_budget": rt.settings.tool_budget,
            "error": (
                f"Tool budget of {rt.settings.tool_budget} calls reached. "
                "Stop calling tools and synthesize the final answer from collected evidence."
            ),
        }
    return None


def gql_dry_run_guard(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> dict | None:
    """graph_query → gql_composer.validate (static schema check + BigQuery dry_run=True)."""
    if _tool_name(tool) != "graph_query":
        return None
    rt = get_runtime()
    card = rt.get_schema_card()
    raw_gql = str(args.get("gql") or "")
    val = gql_composer.validate(
        raw_gql,
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
    args["gql"] = val.gql
    return None


def governance_gate(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> dict | None:
    """fetch_provision requires temp:kc_verdicts[kc_entry_id].readable; BLOCKED → record temp:blocked."""
    if _tool_name(tool) != "fetch_provision":
        return None
    state: Any = getattr(tool_context, "state", None)
    if state is None:
        return None

    slot_id = str(args.get("provision_slot_id") or "").strip()
    verdicts: dict[str, dict[str, Any]] = dict(state.get(sk.KC_VERDICTS) or {})
    if not verdicts:
        return {
            "status": "precondition_failed",
            "provision_slot_id": slot_id,
            "error": (
                "Governance gate violation: `kc_lookup(kc_entry_id)` must be called and return "
                "`ALLOW` or `SUPERSEDED_RESOLVED` before calling `fetch_provision`."
            ),
        }

    # Check if there is a specific matching kc_entry_id for this slot_id (e.g. art_029 -> art-029)
    norm_slot = slot_id.replace("_", "-").lower()
    matched_verdicts = [
        v
        for k, v in verdicts.items()
        if k.lower() == slot_id.lower()
        or k.lower().endswith(norm_slot)
        or norm_slot in k.lower()
    ]
    candidates = matched_verdicts if matched_verdicts else list(verdicts.values())

    for v in candidates:
        if not v.get("readable", False):
            return {
                "status": "blocked_by_governance",
                "provision_slot_id": slot_id,
                "verdict": v.get("verdict"),
                "error": (
                    f"Governance gate blocked `fetch_provision({slot_id})`: "
                    f"KC verdict is `{v.get('verdict')}` ({v.get('reason')})."
                ),
            }
    return None
