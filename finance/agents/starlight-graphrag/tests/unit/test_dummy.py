# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Unit tests for the unified Starlight GraphRAG agent architecture."""

from __future__ import annotations

import hashlib
from types import SimpleNamespace
from typing import Any

from google.adk.models import LlmResponse
from google.genai import types

from app.adapters.incident_sinks import LogIncidentSink
from app.agent import MODEL, app, root_agent
from app.assemblies import build as build_assembly
from app.callbacks.answer import blocked_notice, citation_check, evidence_ledger
from app.callbacks.grounding import load_schema_card, pre_ground_entities
from app.callbacks.guards import governance_gate, gql_dry_run_guard, tool_budget
from app.config import Settings
from app.domain import state_keys as sk
from app.domain.models import GovernanceIncident, GqlDryRunResult, Verdict
from app.runtime import RuntimeContainer, set_runtime
from app.services import alias_resolver, gql_composer, schema_card
from app.services.governance import GovernanceService
from app.services.provision_reader import ProvisionReader
from app.tools import GRAPHRAG_TOOL_NAMES, fetch_provision, graph_query, kc_lookup


class _FakeGraphPort:
    def __init__(self, *, ok: bool = True, bytes_processed: int = 4096, errors: tuple[str, ...] = ()) -> None:
        self._ok = ok
        self._bytes = bytes_processed
        self._errors = errors

    def dry_run_gql(self, gql: str) -> GqlDryRunResult:
        return GqlDryRunResult(ok=self._ok, total_bytes_processed=self._bytes, errors=self._errors)

    def run_gql(self, gql: str, *, max_rows: int) -> dict[str, Any]:
        return {
            "rows": [
                {
                    "contract_id": "LN_2026_KSIC_H1",
                    "customer_id": "CUST_0016",
                    "provision_slot_id": "art_029_1_1_a_proviso",
                    "kc_entry_id": "okf-01-art-029-1-1-a-proviso",
                    "added_min_provision_krw": 135000000,
                }
            ],
            "job_id": "fake-job",
            "bytes_processed": self._bytes,
        }


class _FakeCatalogPort:
    def __init__(self, entries: dict[str, dict[str, Any]] | None = None) -> None:
        self._entries = entries or {}

    def get_graph_anchor_aspect(self) -> dict[str, Any]:
        return _sample_aspect_dict()

    def get_okf_entry(self, kc_entry_id: str) -> dict[str, Any] | None:
        return self._entries.get(kc_entry_id)

    def get_glossary_term(self, term_key: str) -> dict[str, Any] | None:
        return {"term_key": term_key}


class _FakeObjectRefPort:
    def __init__(self, body: str = "건설업(F), 숙박 및 음식점업(H)은 100분의 0.9 이상") -> None:
        self._body = body

    def signed_read_url(self, provision_slot_id: str) -> dict[str, Any]:
        return {
            "provision_slot_id": provision_slot_id,
            "kc_entry_id": "okf-01-art-029-1-1-a-proviso",
            "doc_id": "01",
            "section_number": "제29조제1항제1호가목 단서",
            "source_page": 20,
            "gcs_uri": "gs://finance_okf/okf/01/art_029_1_1_a_proviso.md",
            "read_url": "https://storage.googleapis.com/signed-fake-url",
        }

    def fetch(self, read_url: str) -> str:
        digest = hashlib.sha256(self._body.encode("utf-8")).hexdigest()
        return f"---\nid: art_029_1_1_a_proviso\nsha256: {digest}\n---\n{self._body}\n"


class _FakeAliasPort:
    def load_alias_rows(self) -> list[dict[str, Any]]:
        return [
            {
                "alias_term": "그랜드하모니호텔",
                "target_class": "Customer",
                "match_bind_key": "customer_id",
                "canonical_id": "CUST_0016",
                "canonical_display": "그랜드하모니호텔(주)",
                "gql_match_snippet": "(c:Customer {customer_id: 'CUST_0016'})",
            }
        ]


def _sample_aspect_dict() -> dict[str, Any]:
    return {
        "graph_id": "starlight_bank_ontology.finance_graph",
        "ontology_version": "1.2.0",
        "governance_rule": "status in {'stable', 'verified'}",
        "class_anchors": [
            {
                "class_label": "BusinessContext",
                "layer": "CTX",
                "primary_key": "context_id",
                "anchor_type": "DIRECT_OR_HUB_ANCHOR",
                "gql_match_template": "(ctx:BusinessContext {context_id: '$CANONICAL_ID'})",
            },
            {
                "class_label": "Customer",
                "layer": "LDM",
                "primary_key": "customer_id",
                "anchor_type": "DIRECT_OR_HUB_ANCHOR",
                "gql_match_template": "(c:Customer {customer_id: '$CANONICAL_ID'})",
            },
            {
                "class_label": "LoanContract",
                "layer": "LDM",
                "primary_key": "contract_id",
                "anchor_type": "DIRECT_OR_HUB_ANCHOR",
                "gql_match_template": "(l:LoanContract {contract_id: '$CANONICAL_ID'})",
            },
            {
                "class_label": "Provision",
                "layer": "LEX",
                "primary_key": "provision_slot_id",
                "anchor_type": "DIRECT_OR_HUB_ANCHOR",
                "gql_match_template": "(pr:Provision {provision_slot_id: '$CANONICAL_ID'})",
            },
            {
                "class_label": "WorkoutHistory",
                "layer": "LDM",
                "primary_key": "workout_id",
                "anchor_type": "DIRECT_OR_HUB_ANCHOR",
                "gql_match_template": "(w:WorkoutHistory {workout_id: '$CANONICAL_ID'})",
            },
            {
                "class_label": "RateCutRequest",
                "layer": "LDM",
                "primary_key": "request_id",
                "anchor_type": "DIRECT_OR_HUB_ANCHOR",
                "gql_match_template": "(rc:RateCutRequest {request_id: '$CANONICAL_ID'})",
            },
            {
                "class_label": "SourceDocument",
                "layer": "LEX",
                "primary_key": "doc_id",
                "anchor_type": "DIRECT_OR_HUB_ANCHOR",
                "gql_match_template": "(doc:SourceDocument {doc_id: '$CANONICAL_ID'})",
            },
        ],
        "edge_definitions_json": (
            '[{"edge_label": "BORROWED_BY"}, {"edge_label": "GOVERNED_BY_CRITERIA"}, '
            '{"edge_label": "HAS_EXCEPTION_PROVISO"}, {"edge_label": "HAS_WORKOUT_HISTORY"}, '
            '{"edge_label": "HAS_RATE_CUT_REQUEST"}, {"edge_label": "EVALUATED_UNDER_PROVISION"}, '
            '{"edge_label": "DELEGATES_TO_INTERNAL"}, {"edge_label": "PART_OF_DOCUMENT"}]'
        ),
        "glossary_terms_json": '[{"term_key": "provision-criteria"}]',
    }


def _sample_card():
    return schema_card.from_aspect(_sample_aspect_dict())


def test_root_agent_and_unified_gql_tool_protocol() -> None:
    """Unified GraphRAG agent has 3 GQL/KC/ObjectRef tools and max_graph_hops=12."""
    s = Settings()
    assert s.max_graph_hops == 12
    assert s.max_edge_patterns == 24
    assert root_agent.name == "starlight_graphrag"
    assert type(root_agent).__name__ == "Module05OrchestratorAgent"
    assert MODEL == "gemini-3.8-flash"
    assert app.name == "app"
    assert GRAPHRAG_TOOL_NAMES == (
        "graph_query",
        "kc_lookup",
        "fetch_provision",
    )
    built = build_assembly(s, name="starlight_graphrag", model=MODEL)
    assert len(built.tools) == 3


def test_alias_resolver_longest_match_first() -> None:
    """D3: longest alias wins and prevents short-prefix shadowing."""
    rows = [
        {
            "alias_term": "별빛",
            "target_class": "Customer",
            "match_bind_key": "customer_id",
            "canonical_id": "CUST_0001",
            "canonical_display": "별빛정밀(주)",
            "gql_match_snippet": "(c:Customer {customer_id: 'CUST_0001'})",
        },
        {
            "alias_term": "별빛 프라임 중견기업 운전자금",
            "target_class": "FinancialProduct",
            "match_bind_key": "product_code",
            "canonical_id": "PROD_CORP_PRIME_WC",
            "canonical_display": "별빛 프라임 중견기업 운전자금",
            "gql_match_snippet": "(p:FinancialProduct {product_code: 'PROD_CORP_PRIME_WC'})",
        },
        {
            "alias_term": "리스크관리위원회",
            "target_class": "BusinessContext",
            "match_bind_key": "context_id",
            "canonical_id": "RISK_MGMT",
            "canonical_display": "리스크관리부",
            "gql_match_snippet": "(ctx:BusinessContext {context_id: 'RISK_MGMT'})",
        },
    ]
    q = "리스크관리위원회에 보고할 별빛 프라임 중견기업 운전자금 현황"
    resolved = alias_resolver.resolve(q, rows)
    assert [r.canonical_id for r in resolved] == ["RISK_MGMT", "PROD_CORP_PRIME_WC"]


def test_gql_anchor_template_and_schema_card() -> None:
    """D2 & F3: KC anchor template renders $CANONICAL_ID and render_prompt_block formats 11C/15E."""
    card = _sample_card()
    snippet = gql_composer.render_anchor("(w:WorkoutHistory {workout_id: '$CANONICAL_ID'})", "WK_2025_0001")
    assert snippet == "(w:WorkoutHistory {workout_id: 'WK_2025_0001'})"
    assert card.ontology_version == "1.2.0"
    assert "WorkoutHistory" in card.node_labels
    assert "HAS_WORKOUT_HISTORY" in card.edge_labels
    prompt_md = schema_card.render_prompt_block(card)
    assert "Node Classes & Fixed KC GQL Templates" in prompt_md
    assert "BORROWED_BY" in prompt_md


def test_gql_composer_static_and_dry_run_validation() -> None:
    """D2: GQL Planner output supports up to 12-hop linear chains & star schemas, validated via BQ dry-run."""
    card = _sample_card()
    six_hop_gql = """
    GRAPH starlight_bank_ontology.finance_graph
    MATCH (c:Customer {customer_id: 'CUST_0008'})<-[:BORROWED_BY]-(l:LoanContract)
          -[:HAS_RATE_CUT_REQUEST]->(rc:RateCutRequest)
          -[:EVALUATED_UNDER_PROVISION]->(p_ext:Provision)
          -[:DELEGATES_TO_INTERNAL]->(p_int:Provision)
          -[:HAS_EXCEPTION_PROVISO]->(p_ex:Provision)
          -[:PART_OF_DOCUMENT]->(doc:SourceDocument)
    RETURN c.customer_id, rc.request_id, p_int.provision_slot_id, doc.doc_id
    """
    res_ok = gql_composer.validate(
        six_hop_gql,
        card,
        graph_fqn="starlight_bank_ontology.finance_graph",
        graph_port=_FakeGraphPort(ok=True, bytes_processed=8192),
    )
    assert res_ok.ok is True
    assert res_ok.dry_run_bytes == 8192
    assert "LIMIT 200" in res_ok.gql

    graph_table_gql = """
    SELECT ksic_section_code, SUM(outstanding_amt) AS total_amt
    FROM GRAPH_TABLE(
      starlight_bank_ontology.finance_graph
      MATCH (c:Customer)<-[:BORROWED_BY]-(l:LoanContract)
      COLUMNS (c.ksic_section_code, l.outstanding_amt)
    )
    GROUP BY ksic_section_code
    """
    res_gt = gql_composer.validate(
        graph_table_gql,
        card,
        graph_fqn="starlight_bank_ontology.finance_graph",
        graph_port=_FakeGraphPort(ok=True, bytes_processed=4096),
    )
    assert res_gt.ok is True

    unbounded_gql = "GRAPH starlight_bank_ontology.finance_graph MATCH (p:Provision)-[:HAS_EXCEPTION_PROVISO*]->(q:Provision) RETURN q"
    res_unbounded = gql_composer.validate(unbounded_gql, card, graph_fqn="starlight_bank_ontology.finance_graph")
    assert res_unbounded.ok is False

    bad_label = "GRAPH starlight_bank_ontology.finance_graph MATCH (x:FakeLabel) RETURN x"
    res_bad = gql_composer.validate(bad_label, card, graph_fqn="starlight_bank_ontology.finance_graph")
    assert res_bad.ok is False
    assert any("FakeLabel" in e for e in res_bad.errors)

    res_dry_fail = gql_composer.validate(
        six_hop_gql,
        card,
        graph_fqn="starlight_bank_ontology.finance_graph",
        graph_port=_FakeGraphPort(ok=False, errors=("Unrecognized property foo on LoanContract",)),
    )
    assert res_dry_fail.ok is False
    assert "Unrecognized property foo" in res_dry_fail.errors[0]


def test_governance_service_and_provision_reader_and_callbacks() -> None:
    """End-to-end test of GovernanceService, ProvisionReader, and ADK tool/callback guards."""
    entries = {
        "okf-01-art-029-1-1-a-proviso": {
            "aspects": {"okf": {"data": {"status": "stable", "version": "0.2.0"}}},
            "entrySource": {"resource": "gs://finance_okf/okf/01/art_029_1_1_a_proviso.md"},
        },
        "okf-old-v1": {
            "aspects": {"okf": {"data": {"status": "deprecated", "superseded_by": "okf-01-art-029-1-1-a-proviso"}}},
        },
        "okf-dead-credit-notice": {
            "aspects": {"okf": {"data": {"status": "deprecated", "version": "0.1.0"}}},
        },
    }
    cat = _FakeCatalogPort(entries)
    gov = GovernanceService(cat, okf_aspect_key="okf", max_hops=3)

    assert gov.resolve("okf-01-art-029-1-1-a-proviso").verdict == Verdict.ALLOW
    sup = gov.resolve("okf-old-v1")
    assert sup.verdict == Verdict.SUPERSEDED_RESOLVED
    assert sup.active_entry_id == "okf-01-art-029-1-1-a-proviso"
    blk = gov.resolve("okf-dead-credit-notice")
    assert blk.verdict == Verdict.BLOCKED_DEPRECATED

    # ProvisionReader SHA-256 verification
    reader = ProvisionReader(_FakeObjectRefPort())
    pt = reader.read("art_029_1_1_a_proviso")
    assert pt.sha256_ok is True
    assert "100분의 0.9" in pt.verbatim_body

    # Wire Fake RuntimeContainer and test tools + callbacks
    rt = RuntimeContainer(
        settings=Settings(),
        graph_port=_FakeGraphPort(ok=True, bytes_processed=8192),
        objectref_port=_FakeObjectRefPort(),
        catalog_port=cat,
        alias_port=_FakeAliasPort(),
        incident_sink=LogIncidentSink(),
    )
    set_runtime(rt)
    try:
        ctx = SimpleNamespace(state={"temp:user_query": "그랜드하모니호텔 대출 증액 충당금"}, invocation_id="inv-1", user_id="u-1")
        load_schema_card(ctx)  # type: ignore[arg-type]
        pre_ground_entities(ctx)  # type: ignore[arg-type]
        assert "CUST_0016" in ctx.state[sk.RESOLVED_ENTITIES]

        # Calling fetch_provision BEFORE kc_lookup is blocked by governance_gate
        gate_err = governance_gate(
            SimpleNamespace(name="fetch_provision"),  # type: ignore[arg-type]
            {"provision_slot_id": "art_029_1_1_a_proviso"},
            ctx,  # type: ignore[arg-type]
        )
        assert gate_err is not None and gate_err["status"] == "precondition_failed"

        # Call graph_query -> kc_lookup(ALLOW) -> fetch_provision(ok)
        gq_res = graph_query(
            "GRAPH starlight_bank_ontology.finance_graph MATCH (c:Customer {customer_id: 'CUST_0016'}) RETURN c.customer_id",
            ctx,  # type: ignore[arg-type]
        )
        assert gq_res["status"] == "ok"
        kc_res = kc_lookup("okf-01-art-029-1-1-a-proviso", ctx)  # type: ignore[arg-type]
        assert kc_res["verdict"] == "ALLOW"
        fp_res = fetch_provision("art_029_1_1_a_proviso", ctx)  # type: ignore[arg-type]
        assert fp_res["status"] == "ok" and fp_res["sha256_ok"] is True

        # Now test D5 BLOCKED_DEPRECATED flow: kc_lookup -> evidence_ledger -> blocked_notice
        kc_blk = kc_lookup("okf-dead-credit-notice", ctx)  # type: ignore[arg-type]
        evidence_ledger(
            SimpleNamespace(name="kc_lookup"),  # type: ignore[arg-type]
            {"kc_entry_id": "okf-dead-credit-notice"},
            ctx,  # type: ignore[arg-type]
            kc_blk,
        )
        assert len(ctx.state[sk.BLOCKED]) == 1
        fake_llm_resp = LlmResponse(
            content=types.Content(role="model", parts=[types.Part.from_text(text="추측 답변입니다.")])
        )
        replaced = blocked_notice(ctx, fake_llm_resp)  # type: ignore[arg-type]
        assert replaced is not None
        replaced_text = replaced.content.parts[0].text
        assert "답변드릴 수 없습니다" in replaced_text
        assert "INC-" in replaced_text
    finally:
        set_runtime(None)
