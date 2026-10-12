"""Step 1 validate → repair (≤ max_gql_repairs) → execute once (ADR 0016, user decision 2026-09-29 11:06Z).

Negative controls with in-memory fakes (no BigQuery, no Gemini):
  ① first validation passes          → 0 repairs, 1 execution
  ② one failure, repair passes       → 1 repair, 1 execution, repair sees the failed attempt
  ③ every repair fails               → stops at the cap, 0 executions, refused
  ④ repair hands back a failed GQL   → stops early, 0 executions, refused
  ⑤ refused turn                     → no kc_lookup, no fetch_provision, refusal answer
In every case the GQL is executed at most once.

Free-turn provision slot cap (ADR 0017, user 2026-09-29 12:46Z):
  ⑥ planner GQL touches 50 provisions → planner picks first, 5 slots, tool budget not exhausted
  ⑦ 5 slots or fewer                   → order unchanged (GQL-touched first)
  ⑧ sidebar template path              → never capped
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from app.adapters.incident_sinks import LogIncidentSink
from app.config import Settings
from app.domain.models import GqlDryRunResult
from app.orchestrator import engine
from app.runtime import RuntimeContainer, set_runtime

GOOD_GQL = (
    "GRAPH starlight_bank_ontology.finance_graph\n"
    "MATCH (pr:Provision)-[:PART_OF_DOCUMENT]->(doc:SourceDocument)\n"
    "WHERE doc.doc_id = '06'\n"
    "RETURN pr.kc_entry_id AS kc_entry_id, pr.title AS title\n"
    "LIMIT 50"
)
# The stored EQ10 planner GQL (2026-09-29 08:24Z): BigQuery GQL has no CONTAINS operator.
BAD_GQL = (
    "GRAPH starlight_bank_ontology.finance_graph\n"
    "MATCH (pr:Provision)-[:PART_OF_DOCUMENT]->(doc:SourceDocument)\n"
    "WHERE pr.kc_entry_id CONTAINS 'tf7'\n"
    "RETURN pr.kc_entry_id AS kc_entry_id, pr.title AS title\n"
    "LIMIT 50"
)
SLOT = "regulations/06_fsc_7th_tf_rate_system/sec01_rate_system_maintenance/tf7_01_spread_and_pref_governance"
SYNTAX_ERR = (
    "400 POST https://bigquery.googleapis.com/bigquery/v2/projects/finance-ontology-changseop/queries?prettyPrint=false: "
    "Syntax error: Expected end of input but got keyword CONTAINS at [3:23]\n\n"
    "Location: us-central1\nJob ID: 239840b9-38e6-48f9-8b90-971e7a1a91dc\n"
)


class _FakeGraphPort:
    """Dry-run fails for any GQL containing CONTAINS; counts dry-runs and executions."""

    def __init__(self) -> None:
        self.dry_runs: list[str] = []
        self.executions: list[str] = []

    def dry_run_gql(self, gql: str) -> GqlDryRunResult:
        self.dry_runs.append(gql)
        if "CONTAINS" in gql.upper():
            return GqlDryRunResult(ok=False, total_bytes_processed=0, errors=(SYNTAX_ERR,))
        return GqlDryRunResult(ok=True, total_bytes_processed=34442)

    def run_gql(self, gql: str, *, max_rows: int) -> dict[str, Any]:
        self.executions.append(gql)
        return {"rows": [{"kc_entry_id": SLOT, "title": "정비방향 1"}], "job_id": "job-real-1", "bytes_processed": 34442}


class _FakeCatalogPort:
    def __init__(self) -> None:
        self.okf_lookups: list[str] = []

    def get_graph_anchor_aspect(self) -> dict[str, Any]:
        return {
            "graph_id": "starlight_bank_ontology.finance_graph",
            "ontology_version": "1.2.0",
            "governance_rule": "status in {'stable', 'verified'}",
            "class_anchors": [
                {"class_label": "Provision", "layer": "LEX", "primary_key": "provision_slot_id",
                 "anchor_type": "DIRECT_OR_HUB_ANCHOR", "gql_match_template": "(pr:Provision {provision_slot_id: '$CANONICAL_ID'})"},
                {"class_label": "SourceDocument", "layer": "LEX", "primary_key": "doc_id",
                 "anchor_type": "DIRECT_OR_HUB_ANCHOR", "gql_match_template": "(doc:SourceDocument {doc_id: '$CANONICAL_ID'})"},
            ],
            "edge_definitions_json": '[{"edge_label": "PART_OF_DOCUMENT"}]',
            "glossary_terms_json": "[]",
        }

    def get_okf_entry(self, kc_entry_id: str) -> dict[str, Any] | None:
        self.okf_lookups.append(kc_entry_id)
        return {"aspects": {"okf": {"data": {"status": "stable", "version": "0.2.0"}}}}

    def get_glossary_term(self, term_key: str) -> dict[str, Any] | None:
        return {"term_key": term_key}


class _FakeObjectRefPort:
    def signed_read_url(self, provision_slot_id: str) -> dict[str, Any]:  # pragma: no cover - not reached
        raise AssertionError("fetch goes through resolve_objectrefs_fn in the engine")

    def fetch(self, read_url: str) -> str:  # pragma: no cover
        raise AssertionError("not used")


class _FakeAliasPort:
    def load_alias_rows(self) -> list[dict[str, Any]]:
        return []


@pytest.fixture()
def rt():
    graph, catalog = _FakeGraphPort(), _FakeCatalogPort()
    container = RuntimeContainer(
        settings=Settings(),
        graph_port=graph,
        objectref_port=_FakeObjectRefPort(),
        catalog_port=catalog,
        alias_port=_FakeAliasPort(),
        incident_sink=LogIncidentSink(),
    )
    set_runtime(container)
    try:
        yield SimpleNamespace(graph=graph, catalog=catalog, container=container)
    finally:
        set_runtime(None)


class _Repair:
    """Scripted stand-in for `_gemini_repair_gql`; records what it was shown."""

    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> str:
        self.calls.append(kwargs)
        return self.outputs[min(len(self.calls), len(self.outputs)) - 1]


def _step1(gql: str, repair: _Repair, max_repairs: int = 3) -> dict[str, Any]:
    ctx = SimpleNamespace(state={}, invocation_id="inv-test", user_id="u-test")
    return engine._run_step1_gql(
        gql, adk_ctx=ctx, query_text="7차 TF 논의 항목", alias_hits=[], alias_hits_objs=[], top_examples=[],
        max_repairs=max_repairs, repair_fn=repair,
    )


def test_settings_default_cap_is_three(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STARLIGHT_MAX_GQL_REPAIRS", raising=False)
    assert Settings().max_gql_repairs == 3
    monkeypatch.setenv("STARLIGHT_MAX_GQL_REPAIRS", "5")
    assert Settings().max_gql_repairs == 5


def test_first_validation_passes_executes_once(rt) -> None:
    repair = _Repair([BAD_GQL])
    out = _step1(GOOD_GQL, repair)
    assert out["status"] == "executed"
    assert (out["repair_rounds"], out["validations"], out["executions"]) == (0, 1, 1)
    assert repair.calls == []
    assert len(rt.graph.executions) == 1
    assert out["g_res"]["job_id"] == "job-real-1"


def test_one_failure_then_repair_passes(rt) -> None:
    repair = _Repair([GOOD_GQL])
    out = _step1(BAD_GQL, repair)
    assert out["status"] == "executed"
    assert (out["repair_rounds"], out["validations"], out["executions"]) == (1, 2, 1)
    assert len(rt.graph.executions) == 1 and "CONTAINS" not in rt.graph.executions[0]
    # the repair saw the failed GQL, its error, and the attempt history
    shown = repair.calls[0]
    assert shown["failed_gql"] == BAD_GQL
    assert "CONTAINS" in shown["error_reason"]
    assert [a["gql"] for a in shown["previous_attempts"]] == [BAD_GQL]
    # project identifiers, the REST URL and the trailing job location are stripped from what the UI / prompt see
    err = out["attempts"][0]["errors"][0]
    assert "finance-ontology-changseop" not in err and "https://" not in err and "CONTAINS" in err
    assert "Job ID" not in err and "Location:" not in err and err.endswith("at [3:23]")
    assert [a["ok"] for a in out["attempts"]] == [False, True]


def test_every_repair_fails_stops_at_cap_and_refuses(rt) -> None:
    broken = [BAD_GQL.replace("'tf7'", f"'tf7_{i}'") for i in range(1, 10)]
    repair = _Repair(broken)
    out = _step1(BAD_GQL, repair, max_repairs=3)
    assert out["status"] == "refused" and out["stop_reason"] == "max_repairs"
    assert (out["repair_rounds"], out["validations"], out["executions"]) == (3, 4, 0)
    assert len(repair.calls) == 3
    assert rt.graph.executions == []
    # each round is shown every earlier failure
    assert [len(c["previous_attempts"]) for c in repair.calls] == [1, 2, 3]


def test_repeated_gql_stops_early_and_refuses(rt) -> None:
    repair = _Repair([BAD_GQL.replace("\n", "\n  ")])  # same GQL, different whitespace
    out = _step1(BAD_GQL, repair, max_repairs=3)
    assert out["status"] == "refused" and out["stop_reason"] == "repeated_gql"
    assert (out["repair_rounds"], out["validations"], out["executions"]) == (1, 1, 0)
    assert out["attempts"][-1].get("repeated") is True
    assert rt.graph.executions == []


def test_repair_call_error_uses_a_round_and_loop_continues(rt) -> None:
    calls = {"n": 0}

    def flaky(**kwargs: Any) -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("500 INTERNAL")
        return GOOD_GQL

    ctx = SimpleNamespace(state={}, invocation_id="inv-test", user_id="u-test")
    out = engine._run_step1_gql(
        BAD_GQL, adk_ctx=ctx, query_text="q", alias_hits=[], alias_hits_objs=[], top_examples=[],
        max_repairs=3, repair_fn=flaky,
    )
    assert out["status"] == "executed"
    assert (out["repair_rounds"], out["validations"], out["executions"]) == (2, 2, 1)
    assert out["attempts"][1].get("repair_error") is True


def test_zero_cap_means_no_repair(rt) -> None:
    repair = _Repair([GOOD_GQL])
    out = _step1(BAD_GQL, repair, max_repairs=0)
    assert out["status"] == "refused" and out["stop_reason"] == "max_repairs"
    assert repair.calls == [] and rt.graph.executions == []


# --- through execute_agent_chat -------------------------------------------------------------


def _patch_turn(monkeypatch: pytest.MonkeyPatch, repair_outputs: list[str]) -> _Repair:
    repair = _Repair(repair_outputs)
    monkeypatch.setattr(engine, "_retrieve_top_gql_examples", lambda q, n=None, top_k=3: ("CQ01", None, 10, []))
    monkeypatch.setattr(engine, "_load_provision_catalog", lambda fn: [{"kc_entry_id": SLOT, "title": "정비방향 1"}])
    monkeypatch.setattr(engine, "_gemini_plan_turn", lambda **kw: {
        "mode": "FULL_GRAPHRAG", "reason": "test", "dept_id": "RISK_MGMT", "matched_cq_id": "",
        "gql": BAD_GQL, "provision_slots": [SLOT], "direct_response_markdown": "",
    })
    monkeypatch.setattr(engine, "_gemini_repair_gql", repair)
    monkeypatch.setattr(engine, "_gemini_synthesize_briefing", lambda **kw: "브리핑")
    return repair


def test_turn_refused_runs_no_kc_lookup_or_fetch(rt, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_turn(monkeypatch, [BAD_GQL.replace("'tf7'", f"'x{i}'") for i in range(1, 10)])
    fetch_calls: list[Any] = []

    res = engine.execute_agent_chat(
        {"question": "7차 TF 회의에서 논의된 항목은?"},
        run_bq_sql_fn=lambda sql: ([], {}),
        resolve_objectrefs_fn=lambda slots, extra: fetch_calls.append(slots) or ({}, {"total_bytes": 0}),
    )
    tr, qa = res["adk_trace"], res["gql_accordion"]
    assert res["refused"] is True and res["internal_key"] == "GQL_REFUSED"
    assert "답변 거절" in res["answer_markdown"]
    assert "finance-ontology-changseop" not in res["answer_markdown"]
    assert tr["gql_status"] == "refused" and tr["gql_executions"] == 0 and tr["gql_repair_rounds"] == 3
    assert qa["job_id"] == "" and len(qa["gql_attempts"]) == 4
    assert rt.catalog.okf_lookups == []  # no kc_lookup
    assert fetch_calls == []  # no fetch_provision
    assert rt.graph.executions == []
    assert [e["tool"] for e in tr["evidence_ledger"]] == ["graph_query"]


def test_turn_repaired_executes_once_then_continues(rt, monkeypatch: pytest.MonkeyPatch) -> None:
    repair = _patch_turn(monkeypatch, [GOOD_GQL])
    fetch_calls: list[Any] = []

    res = engine.execute_agent_chat(
        {"question": "7차 TF 회의에서 논의된 항목은?"},
        run_bq_sql_fn=lambda sql: ([], {}),
        resolve_objectrefs_fn=lambda slots, extra: fetch_calls.append(list(slots)) or ({}, {"total_bytes": 0}),
    )
    tr, qa = res["adk_trace"], res["gql_accordion"]
    assert not res.get("refused")
    assert tr["gql_status"] == "executed" and tr["gql_executions"] == 1 and tr["gql_repair_rounds"] == 1
    assert tr["gql_repaired"] is True and qa["job_id"] == "job-real-1"
    assert "교정 1회" in qa["title"]
    assert len(repair.calls) == 1 and len(rt.graph.executions) == 1
    assert tr["touched_kc_entry_ids"] == [SLOT]
    assert rt.catalog.okf_lookups == [SLOT]  # kc_lookup ran on the GQL-touched slot
    assert fetch_calls == [[SLOT]]


# --- free-turn provision slot cap (ADR 0017) --------------------------------------------------

PICKS = [f"regulations/06_fsc_7th_tf_rate_system/sec01/tf7_0{i}" for i in (1, 2, 3)]  # planner's catalog-validated picks


def _touched(n: int) -> list[str]:
    return [f"regulations/01_fsc_banking_reg/ch01/art_{i:03d}" for i in range(1, n + 1)]


def test_merge_slots_helper() -> None:
    merge, cap = engine._merge_provision_slots, engine._MAX_FREE_TURN_PROVISION_SLOTS
    assert cap == 5
    # at or under the cap, or without a cap: unchanged order (GQL-touched first), de-duplicated
    assert merge(_touched(3), PICKS[:2], cap=cap) == [*_touched(3), *PICKS[:2]]
    assert merge([PICKS[0], *_touched(2)], PICKS, cap=cap) == [PICKS[0], *_touched(2), *PICKS[1:]]
    assert merge(_touched(50), PICKS, cap=None) == [*_touched(50), *PICKS]
    # over the cap: the fallback (planner) slots first, then GQL-touched, cut at the cap
    assert merge(_touched(50), PICKS, cap=cap) == [*PICKS, *_touched(2)]
    assert merge(_touched(8), [], cap=cap) == _touched(5)


def _patch_free_turn(rt, monkeypatch: pytest.MonkeyPatch, touched: list[str], picks: list[str],
                     best_score: int = 10) -> list[Any]:
    monkeypatch.setattr(engine, "_retrieve_top_gql_examples", lambda q, n=None, top_k=3: ("CQ01", None, best_score, []))
    monkeypatch.setattr(engine, "_load_provision_catalog",
                        lambda fn: [{"kc_entry_id": s, "title": s.rsplit("/", 1)[-1]} for s in picks])
    monkeypatch.setattr(engine, "_gemini_plan_turn", lambda **kw: {
        "mode": "FULL_GRAPHRAG", "reason": "test", "dept_id": "RISK_MGMT", "matched_cq_id": "",
        "gql": GOOD_GQL, "provision_slots": list(picks), "direct_response_markdown": "",
    })
    monkeypatch.setattr(engine, "_gemini_repair_gql", _Repair([GOOD_GQL]))
    monkeypatch.setattr(engine, "_gemini_synthesize_briefing", lambda **kw: "브리핑")
    rows = [{"kc_entry_id": s, "title": s.rsplit("/", 1)[-1]} for s in touched]
    monkeypatch.setattr(rt.graph, "run_gql",
                        lambda gql, *, max_rows: {"rows": rows, "job_id": "job-wide", "bytes_processed": 1})
    fetch_calls: list[Any] = []
    res = engine.execute_agent_chat(
        {"question": "제7차 은행권 TF 에서 논의된 금리산정체계 정비 항목은?"},
        run_bq_sql_fn=lambda sql: ([], {}),
        resolve_objectrefs_fn=lambda slots, extra: fetch_calls.append(list(slots)) or ({}, {"total_bytes": 0}),
    )
    return [res, fetch_calls]


def _budget_blocks(tr: dict[str, Any]) -> int:
    """Budget-blocked calls as the engine records them: fetches in `governance_gate_blocks`, kc_lookups in the ledger."""
    fetch = [b for b in tr.get("governance_gate_blocks") or [] if b.get("status") == "budget_exhausted"]
    kc = [e for e in tr.get("evidence_ledger") or []
          if e.get("tool") == "kc_lookup" and "status=budget_exhausted" in str(e.get("summary"))]
    return len(fetch) + len(kc)


def test_free_turn_wide_gql_keeps_planner_picks_within_budget(rt, monkeypatch: pytest.MonkeyPatch) -> None:
    # EQ10 12:09Z: the repaired GQL lost its WHERE and touched 50 unrelated provisions; the 3 planner picks came
    # 51st–53rd and the budget ran out before any fetch. Now they come first and all 5 slots are fetched.
    res, fetch_calls = _patch_free_turn(rt, monkeypatch, _touched(50), PICKS)
    tr = res["adk_trace"]
    assert len(tr["touched_kc_entry_ids"]) == 50
    assert rt.catalog.okf_lookups == [*PICKS, *_touched(2)]  # kc_lookup order
    assert fetch_calls == [[*PICKS, *_touched(2)]]
    assert tr["tool_calls_used"] == 11 <= rt.container.settings.tool_budget  # graph_query 1 + 5 + 5
    assert _budget_blocks(tr) == 0


def test_free_turn_small_gql_order_unchanged(rt, monkeypatch: pytest.MonkeyPatch) -> None:
    res, fetch_calls = _patch_free_turn(rt, monkeypatch, _touched(3), PICKS[:1])
    assert rt.catalog.okf_lookups == [*_touched(3), PICKS[0]]  # 4 ≤ 5: GQL-touched first, as before
    assert fetch_calls == [[*_touched(3), PICKS[0]]]
    assert res["adk_trace"]["tool_calls_used"] == 9


def test_template_path_is_never_capped(rt, monkeypatch: pytest.MonkeyPatch) -> None:
    # best_score 100 = sidebar click: the verified template GQL and CQ slots, no cap (same as before ADR 0017)
    monkeypatch.setitem(engine.CQ_GQL_TEMPLATES, "CQ01", GOOD_GQL)
    res, _ = _patch_free_turn(rt, monkeypatch, _touched(8), [], best_score=100)
    tr = res["adk_trace"]
    assert len(rt.catalog.okf_lookups) > engine._MAX_FREE_TURN_PROVISION_SLOTS
    assert rt.catalog.okf_lookups[:8] == _touched(8)  # GQL-touched first, uncapped
    assert tr["tool_calls_used"] > rt.container.settings.tool_budget  # the old budget behaviour is untouched
    assert _budget_blocks(tr) > 0  # and the counter used above does see budget-blocked calls
