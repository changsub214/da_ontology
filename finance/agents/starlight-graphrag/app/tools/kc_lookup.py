"""kc_lookup — LLM-facing wrapper. Logic lives in services/governance."""

from __future__ import annotations

from typing import Any

from google.adk.tools import ToolContext

from app.domain import state_keys as sk
from app.runtime import get_runtime


def kc_lookup(kc_entry_id: str, tool_context: ToolContext) -> dict[str, Any]:
    """Check whether a provision is currently valid in the Knowledge Catalog.

    Must be called for a provision before `fetch_provision`. Deprecated provisions are
    followed to their verified replacement (up to 3 hops).

    Args:
        kc_entry_id: The `kc_entry_id` returned by graph_query for a Provision node.

    Returns:
        {"verdict": "ALLOW" | "SUPERSEDED_RESOLVED" | "BLOCKED_*", "active_entry_id": ...,
         "status": ..., "version": ..., "chain": [...]}
    """
    rt = get_runtime()
    res = rt.governance_service.resolve(kc_entry_id)
    payload = {
        "requested_entry_id": res.requested_entry_id,
        "verdict": res.verdict.value,
        "readable": res.verdict.readable,
        "active_entry_id": res.active_entry_id,
        "status": res.status,
        "version": res.version,
        "chain": list(res.chain),
        "gcs_uri": res.gcs_uri,
        "reason": res.reason,
    }
    state = getattr(tool_context, "state", None)
    if state is not None:
        verdicts = dict(state.get(sk.KC_VERDICTS) or {})
        verdicts[kc_entry_id] = payload
        if res.active_entry_id:
            verdicts[res.active_entry_id] = payload
        state[sk.KC_VERDICTS] = verdicts
    return payload
