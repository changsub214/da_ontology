"""`Module05OrchestratorAgent` — runs the local Module 05 pipeline unchanged inside ADK.

The deployed root agent must behave exactly like the local studio (`05 · agent`):
Step 0 alias/anchor binding → `gemini-3.8-flash` turn plan (OUT_OF_DOMAIN / META_HELP /
LEDGER_ONLY / FULL_GRAPHRAG) → GQL validate → repair (≤3, ADR 0016) → one `graph_query` → `kc_lookup` →
`fetch_provision` → briefing → `blocked_notice` / `citation_check` (refused if no GQL passes validation).

That control flow lives in `app.orchestrator.engine.execute_agent_chat`. A free `LlmAgent`
would let the model decide how many tools to call, which is exactly the divergence that was
measured on the first deployment (4 exploratory `graph_query` calls in one turn), so this
agent does not delegate control to an LLM loop at all.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

from app.orchestrator.engine import execute_agent_chat

_DONE = object()


def _payload_from_user_content(ctx: InvocationContext) -> dict[str, Any]:
    """Accepts either a JSON payload (`{"num": "01", "question": ...}`) or plain text."""
    text = ""
    content = ctx.user_content
    if content and content.parts:
        text = "".join(p.text or "" for p in content.parts if getattr(p, "text", None)).strip()
    if text.startswith("{"):
        try:
            data = json.loads(text)
            if isinstance(data, dict) and (data.get("question") or data.get("query")):
                return data
        except json.JSONDecodeError:
            pass
    return {"question": text}


def _jsonable(obj: Any) -> Any:
    return json.loads(json.dumps(obj, ensure_ascii=False, default=str))


class Module05OrchestratorAgent(BaseAgent):
    """Deterministic Module 05 orchestrator exposed as an ADK agent."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        payload = _payload_from_user_content(ctx)
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[Any] = asyncio.Queue()

        def _on_stage(msg: str) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, msg)

        async def _run() -> dict[str, Any]:
            try:
                return await asyncio.to_thread(execute_agent_chat, payload, on_stage=_on_stage)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, _DONE)

        task = asyncio.create_task(_run())
        while True:
            item = await queue.get()
            if item is _DONE:
                break
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                partial=True,
                custom_metadata={"type": "stage", "text": str(item)},
            )

        try:
            result = await task
        except Exception as exc:  # surface as a model turn instead of a 500
            yield Event(
                invocation_id=ctx.invocation_id,
                author=self.name,
                branch=ctx.branch,
                content=types.Content(
                    role="model",
                    parts=[types.Part(text=f"요청 처리 중 오류가 발생했습니다: {type(exc).__name__}: {exc}")],
                ),
                error_code="ORCHESTRATOR_ERROR",
                error_message=str(exc)[:500],
            )
            return

        answer_md = str(result.get("answer_markdown") or "")
        meta = _jsonable({k: v for k, v in result.items() if k != "answer_markdown"})
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            content=types.Content(role="model", parts=[types.Part(text=answer_md)]),
            custom_metadata={"type": "module05_result", **meta},
        )
