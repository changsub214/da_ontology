#!/usr/bin/env python3
"""Workstation shim for Module 05 (`05 · agent`) → packaged orchestrator.

The Module 05 orchestrator used to live here and was never deployed, so the Agent Runtime
agent (`starlight-graphrag`) ran a different, free LlmAgent loop. It now lives in
`agents/starlight-graphrag/app/orchestrator/engine.py` and is the root agent of the
deployed package. This shim keeps `tools/studio_server.py` imports (`execute_agent_chat`,
`get_agent_questions`) working so the local UI and Agent Runtime execute the same code.
See ADR 0007.

Mode switch (`STARLIGHT_AGENT_MODE`, default `local`):
  - `local`  : run `engine.execute_agent_chat` in-process (imports ADK etc. on first chat).
  - `remote` : call the deployed Agent Runtime via `tools/agent_remote_client.py` — same
               signature and result shape, so the studio server and UI are unchanged.
`get_agent_questions` is served in both modes from the dependency-light
`app/orchestrator/questions.py`, loaded by file path so `app/__init__.py` (ADK) is not imported.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from typing import Any, Callable

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ.setdefault("GOOGLE_API_USE_MTLS_ENDPOINT", "never")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENT_PKG_DIR = os.path.join(_ROOT, "finance", "agents", "starlight-graphrag")
# Workstation reads the SSOT directly; the deployed package reads its hash-checked copy.
os.environ.setdefault("STARLIGHT_CQ_YAML", os.path.join(_ROOT, "finance", "ontology", "cq", "competency_questions.yaml"))

MODE = os.environ.get("STARLIGHT_AGENT_MODE", "local").strip().lower()
if MODE not in ("local", "remote"):
    raise ValueError(f"STARLIGHT_AGENT_MODE must be 'local' or 'remote', got {MODE!r}")


def _load_questions_module() -> Any:
    path = os.path.join(_AGENT_PKG_DIR, "app", "orchestrator", "questions.py")
    spec = importlib.util.spec_from_file_location("starlight_agent_questions", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


get_agent_questions = _load_questions_module().get_agent_questions


def execute_agent_chat(data: dict[str, Any], on_stage: Callable[[str], None] | None = None) -> dict[str, Any]:
    if MODE == "remote":
        from agent_remote_client import execute_agent_chat as _remote

        return _remote(data, on_stage=on_stage)
    if _AGENT_PKG_DIR not in sys.path:
        sys.path.insert(0, _AGENT_PKG_DIR)
    from app.orchestrator.engine import execute_agent_chat as _local

    return _local(data, on_stage=on_stage)


def execute_kmarket_agent_chat(
    data: dict[str, Any],
    run_bq_sql_fn: Any = None,
    resolve_bq_objectrefs_fn: Any = None,
    on_stage: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    kmarket_meta = os.path.join(_ROOT, "ecommerce", "agents", "kmarket-graph-agent", "deployment_metadata.json")
    explicit_mode = os.environ.get("STARLIGHT_AGENT_MODE", "").strip().lower()
    use_remote = (explicit_mode == "remote") or (
        explicit_mode != "local" and (bool(os.environ.get("KMARKET_AGENT_RESOURCE")) or os.path.exists(kmarket_meta))
    )
    if use_remote:
        from agent_remote_client import execute_kmarket_agent_chat as _remote_km

        return _remote_km(data, on_stage=on_stage)
    from ecommerce_agent_handler import execute_ecommerce_agent_chat as _local_km

    return _local_km(data, run_bq_sql_fn, resolve_bq_objectrefs_fn, on_stage=on_stage)


__all__ = ["MODE", "execute_agent_chat", "execute_kmarket_agent_chat", "get_agent_questions"]
