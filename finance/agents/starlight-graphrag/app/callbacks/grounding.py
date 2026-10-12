"""before_agent callbacks: schema card (KC) + D3 pre-grounding (aliases).

D3 decision: entity resolution runs here, not as a tool —
  every turn needs it · deterministic · in-process (µs–ms, cached 438 rows) ·
  the LLM does not need to choose arguments · saves ≥1 model round trip + 1 budget slot.
"""

from __future__ import annotations

from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from app.domain import state_keys as sk
from app.runtime import get_runtime
from app.services import alias_resolver, gql_composer, schema_card


def _extract_user_text(callback_context: CallbackContext) -> str:
    user_content = getattr(callback_context, "user_content", None)
    if user_content and getattr(user_content, "parts", None):
        parts_txt = [
            getattr(p, "text", "") or ""
            for p in user_content.parts
            if getattr(p, "text", None)
        ]
        if parts_txt:
            return "\n".join(parts_txt).strip()
    state = getattr(callback_context, "state", None)
    if state is not None:
        return str(state.get("temp:user_query") or "")
    return ""


def load_schema_card(callback_context: CallbackContext) -> types.Content | None:
    """Populate `app:schema_card` from KC aspect and reset turn-scoped `temp:*` state."""
    state: Any = getattr(callback_context, "state", None)
    if state is None:
        return None

    # Reset per-turn state
    state[sk.TOOL_CALLS_USED] = 0
    state[sk.KC_VERDICTS] = {}
    state[sk.EVIDENCE] = []
    state[sk.BLOCKED] = []

    if not state.get(sk.SCHEMA_CARD):
        rt = get_runtime()
        card = rt.get_schema_card()
        state[sk.SCHEMA_CARD] = schema_card.render_prompt_block(card)
    return None


def pre_ground_entities(callback_context: CallbackContext) -> types.Content | None:
    """Resolve user query aliases (438 rows longest-match) and bind KC `gql_match_template`."""
    state: Any = getattr(callback_context, "state", None)
    if state is None:
        return None

    user_text = _extract_user_text(callback_context)
    if not user_text:
        state[sk.RESOLVED_ENTITIES] = "(질문 텍스트 없음)"
        return None

    rt = get_runtime()
    alias_rows = rt.get_alias_rows()
    card = rt.get_schema_card()
    entities = alias_resolver.resolve(user_text, alias_rows)
    snippets = gql_composer.anchors_for(entities, card)

    if not entities:
        state[sk.RESOLVED_ENTITIES] = "(직접 매칭된 고유명사/용어 별칭 없음 — 스키마 카드 기준 탐색)"
        return None

    lines: list[str] = []
    for ent, snip in zip(entities, snippets):
        lines.append(
            f"- `{ent.alias_term}` → [{ent.target_class}] `{ent.canonical_id}` ({ent.canonical_display}) "
            f"| KC 고정 앵커: `{snip}`"
        )
    state[sk.RESOLVED_ENTITIES] = "\n".join(lines)
    return None
