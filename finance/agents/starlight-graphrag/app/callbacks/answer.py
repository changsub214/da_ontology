"""after_tool / after_model callbacks: evidence ledger, D5 blocked notice, citation check."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse
from google.adk.tools import BaseTool, ToolContext
from google.genai import types

from app.domain import state_keys as sk
from app.domain.models import GovernanceIncident, Verdict
from app.prompts import load as load_prompt
from app.runtime import get_runtime


def _tool_name(tool: BaseTool | Any) -> str:
    return str(getattr(tool, "name", None) or getattr(tool, "__name__", "") or "")


def _make_incident_id(kc_entry_id: str) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    short = hashlib.sha1(kc_entry_id.encode("utf-8")).hexdigest()[:6].upper()
    return f"INC-{today}-{short}"


def evidence_ledger(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, tool_response: dict
) -> dict | None:
    """Append EvidenceItem to temp:evidence; store kc_lookup verdicts in temp:kc_verdicts;
    if BLOCKED_DEPRECATED, record temp:blocked and emit GovernanceIncident via IncidentSinkPort."""
    state: Any = getattr(tool_context, "state", None)
    if state is None or not isinstance(tool_response, dict):
        return None

    tname = _tool_name(tool)
    ev_list = list(state.get(sk.EVIDENCE) or [])
    step_no = int(state.get(sk.TOOL_CALLS_USED) or len(ev_list) + 1)

    if tname == "graph_query":
        key = str(args.get("gql") or "")[:120]
        summary = f"status={tool_response.get('status')} rows={tool_response.get('row_count', 0)} dry_run_bytes={tool_response.get('dry_run_bytes', 0)}"
    elif tname == "kc_lookup":
        key = str(args.get("kc_entry_id") or "")
        verdict_str = str(tool_response.get("verdict") or "")
        summary = f"verdict={verdict_str} active={tool_response.get('active_entry_id')} status={tool_response.get('status')}"
        if verdict_str.startswith("BLOCKED"):
            rt = get_runtime()
            inc_id = _make_incident_id(key)
            q_raw = str(state.get("temp:user_query") or "")
            q_sha = hashlib.sha256(q_raw.encode("utf-8")).hexdigest()
            incident = GovernanceIncident(
                incident_id=inc_id,
                occurred_at=datetime.now(timezone.utc).isoformat(),
                session_id=str(getattr(tool_context, "invocation_id", "") or "sess-local"),
                user_id=str(getattr(tool_context, "user_id", "") or "user-local"),
                kc_entry_id=key,
                provision_slot_id=None,
                verdict=verdict_str,
                chain=tuple(tool_response.get("chain") or ()),
                question_sha256=q_sha,
            )
            rt.incident_sink.emit(incident)
            blocked_list = list(state.get(sk.BLOCKED) or [])
            blocked_list.append(
                {
                    "incident_id": inc_id,
                    "kc_entry_id": key,
                    "verdict": verdict_str,
                    "reason": str(tool_response.get("reason") or "Provision is deprecated with no valid replacement."),
                }
            )
            state[sk.BLOCKED] = blocked_list
            tool_response["incident_id"] = inc_id
    elif tname == "fetch_provision":
        key = str(args.get("provision_slot_id") or "")
        summary = f"doc={tool_response.get('doc_id')} sec={tool_response.get('section_number')} p={tool_response.get('source_page')} sha256_ok={tool_response.get('sha256_ok')}"
    else:
        key = str(args)
        summary = str(tool_response)[:120]

    ev_list.append({"step": step_no, "tool": tname, "key": key, "summary": summary})
    state[sk.EVIDENCE] = ev_list
    return None


def blocked_notice(callback_context: CallbackContext, llm_response: LlmResponse) -> LlmResponse | None:
    """D5: if temp:blocked non-empty → refuse answer and replace with prompts/blocked_notice.md."""
    state: Any = getattr(callback_context, "state", None)
    if state is None:
        return None
    blocked_list = list(state.get(sk.BLOCKED) or [])
    if not blocked_list:
        return None

    inc_id = str(blocked_list[0].get("incident_id") or "INC-PENDING")
    kc_id = str(blocked_list[0].get("kc_entry_id") or "")
    reason = str(blocked_list[0].get("reason") or "")
    notice_text = load_prompt("blocked_notice").replace("{incident_id}", inc_id)
    if kc_id:
        notice_text += f"\n- 차단 대상 카탈로그 엔트리: `{kc_id}` ({reason})"

    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part.from_text(text=notice_text)],
        )
    )


_CITATION_RE = re.compile(r"(제\s*\d+\s*조|별표\s*\d+|\b0[1-9]\b|\b10\b|p\.\s*\d+|\d+\s*쪽)")


def citation_check(callback_context: CallbackContext, llm_response: LlmResponse) -> LlmResponse | None:
    """Final answer must cite doc id (01–10) + article/page for every provision used."""
    state: Any = getattr(callback_context, "state", None)
    if state is None or state.get(sk.BLOCKED):
        return None

    # Only enforce when final text response is emitted (no pending function calls)
    content = getattr(llm_response, "content", None)
    if not content or not getattr(content, "parts", None):
        return None
    if any(getattr(p, "function_call", None) for p in content.parts):
        return None

    text = "\n".join(getattr(p, "text", "") or "" for p in content.parts).strip()
    if not text:
        return None

    ev_list = list(state.get(sk.EVIDENCE) or [])
    fetched = [e for e in ev_list if e.get("tool") == "fetch_provision"]
    if fetched and not _CITATION_RE.search(text):
        refs = ", ".join(e.get("summary", "") for e in fetched)
        appended = f"{text}\n\n**[근거 문헌 인용 보강]** {refs}"
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=appended)],
            )
        )
    return None
