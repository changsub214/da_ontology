"""Shared helpers for tool wrappers."""

from __future__ import annotations

from typing import Any


def not_ready(tool: str) -> dict[str, Any]:
    """Structured placeholder while Phase 2 is pending (never raises into the agent loop)."""
    return {"status": "not_implemented", "tool": tool, "message": f"{tool} is scaffolded but not wired yet."}
