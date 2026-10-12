"""Callback chains for the unified Starlight GraphRAG agent."""

from __future__ import annotations

from app.callbacks.answer import blocked_notice, citation_check, evidence_ledger
from app.callbacks.grounding import load_schema_card, pre_ground_entities
from app.callbacks.guards import governance_gate, gql_dry_run_guard, tool_budget

BEFORE_AGENT = [load_schema_card, pre_ground_entities]
BEFORE_TOOL = [tool_budget, gql_dry_run_guard, governance_gate]
AFTER_TOOL = [evidence_ledger]
AFTER_MODEL = [blocked_notice, citation_check]
