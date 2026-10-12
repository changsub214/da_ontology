"""Prompt loader — prompts are markdown files, not Python strings, so they can be reviewed/diffed."""

from __future__ import annotations

from functools import cache
from pathlib import Path

_DIR = Path(__file__).parent


@cache
def load(name: str) -> str:
    return (_DIR / f"{name}.md").read_text(encoding="utf-8")


def graphrag_instruction(*, tool_budget: int) -> str:
    """common skeleton (shared with RAG arm) + GraphRAG tool paragraph.

    `{tool_budget}` is rendered here; `{temp:...}` / `{app:...}` stay for ADK state injection.
    """
    return load("common_skeleton") + "\n\n" + load("graph_tools").replace("{tool_budget}", str(tool_budget))
