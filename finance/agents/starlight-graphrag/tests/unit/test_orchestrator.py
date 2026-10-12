"""Parity guards for the packaged Module 05 orchestrator (ADR 0007)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from google.genai import types

from app.orchestrator import engine
from app.orchestrator.agent import _payload_from_user_content

_PKG_ROOT = Path(__file__).resolve().parents[2]
_PACKAGED_CQ = _PKG_ROOT / "app" / "data" / "competency_questions.yaml"
_SSOT_CQ = _PKG_ROOT.parents[1] / "ontology" / "cq" / "competency_questions.yaml"
_LOCAL_SHIM = _PKG_ROOT.parents[2] / "tools" / "agent_chat_engine.py"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_packaged_cq_yaml_matches_ssot() -> None:
    """The deployed agent must see the same CQ anchors as the workstation UI."""
    if not _SSOT_CQ.exists():
        pytest.skip("SSOT ontology/cq/competency_questions.yaml not present (packaged build)")
    assert _sha(_PACKAGED_CQ) == _sha(_SSOT_CQ), (
        "app/data/competency_questions.yaml drifted from ontology/cq SSOT; re-copy before deploy"
    )


def test_packaged_cqs_load() -> None:
    qs = engine.get_agent_questions()
    assert len(qs) >= 20


def test_engine_has_no_workstation_paths() -> None:
    src = Path(engine.__file__).read_text(encoding="utf-8")
    assert "/home/" not in src
    assert "sys.path" not in src


def test_local_shim_reexports_packaged_engine() -> None:
    """Local studio must not carry its own orchestrator copy.

    The shim may hold a thin local/remote dispatcher (`STARLIGHT_AGENT_MODE`), but local mode must
    delegate to the packaged engine and no orchestration logic may live in the shim.
    """
    if not _LOCAL_SHIM.exists():
        pytest.skip("workstation shim not present (packaged build)")
    src = _LOCAL_SHIM.read_text(encoding="utf-8")
    assert "from app.orchestrator.engine import" in src
    assert "from agent_remote_client import" in src
    for marker in ("_gemini", "run_bq_sql", "gql_composer", "kc_lookup", "CONVERSATIONAL_BRIEFINGS"):
        assert marker not in src, f"orchestration logic leaked into the shim: {marker}"


_QUESTIONS_SRC = _PKG_ROOT / "app" / "orchestrator" / "questions.py"


def test_questions_module_is_dependency_light() -> None:
    """The web tier loads questions.py by path; it must not pull ADK / genai / app.* imports."""
    src = _QUESTIONS_SRC.read_text(encoding="utf-8")
    for banned in ("from app", "import app", "google.adk", "google.genai", "bigquery"):
        assert banned not in src, banned


def test_engine_reexports_questions() -> None:
    from app.orchestrator import questions

    assert engine.get_agent_questions is questions.get_agent_questions
    assert engine._load_cqs is questions._load_cqs


def _ctx(text: str) -> SimpleNamespace:
    return SimpleNamespace(user_content=types.Content(role="user", parts=[types.Part(text=text)]))


def test_payload_parsing_plain_and_json() -> None:
    assert _payload_from_user_content(_ctx("  안녕 ")) == {"question": "안녕"}  # type: ignore[arg-type]
    js = json.dumps({"num": "01", "question": "q"}, ensure_ascii=False)
    assert _payload_from_user_content(_ctx(js)) == {"num": "01", "question": "q"}  # type: ignore[arg-type]
    assert _payload_from_user_content(_ctx("{not json")) == {"question": "{not json"}  # type: ignore[arg-type]
