"""Domain models shared by services, tools and callbacks (no GCP / ADK imports)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class ResolvedEntity:
    """One alias span resolved from the user query (ont_entity_aliases longest-match)."""

    span: tuple[int, int]
    alias_term: str
    target_class: str
    match_bind_key: str
    canonical_id: str
    canonical_display: str
    gql_match_snippet: str


@dataclass(frozen=True)
class ClassAnchor:
    """One entry of KC aspect `ontology-class-anchors.class_anchors`."""

    class_label: str
    layer: str
    primary_key: str
    anchor_type: str
    gql_match_template: str  # e.g. "(c:Customer {customer_id: '$CANONICAL_ID'})"


@dataclass(frozen=True)
class SchemaCard:
    """Graph schema the LLM/Planner sees: anchors + edge definitions + glossary, loaded from KC."""

    graph_id: str
    ontology_version: str
    governance_rule: str
    anchors: tuple[ClassAnchor, ...]
    edges: tuple[dict[str, Any], ...]
    glossary_terms: tuple[dict[str, Any], ...]

    @property
    def node_labels(self) -> frozenset[str]:
        return frozenset(a.class_label for a in self.anchors)

    @property
    def edge_labels(self) -> frozenset[str]:
        return frozenset(str(e.get("edge_label")) for e in self.edges)


@dataclass(frozen=True)
class GqlDryRunResult:
    """Result of BigQuery dry-run validation (`QueryJobConfig(dry_run=True)`)."""

    ok: bool
    total_bytes_processed: int = 0
    errors: tuple[str, ...] = ()


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    SUPERSEDED_RESOLVED = "SUPERSEDED_RESOLVED"
    BLOCKED_DEPRECATED = "BLOCKED_DEPRECATED"
    BLOCKED_NOT_FOUND = "BLOCKED_NOT_FOUND"
    BLOCKED_MAX_DEPTH_EXCEEDED = "BLOCKED_MAX_DEPTH_EXCEEDED"

    @property
    def readable(self) -> bool:
        return self in (Verdict.ALLOW, Verdict.SUPERSEDED_RESOLVED)


@dataclass(frozen=True)
class KcVerdict:
    requested_entry_id: str
    verdict: Verdict
    active_entry_id: str | None = None
    status: str | None = None
    version: str | None = None
    chain: tuple[str, ...] = ()
    gcs_uri: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class ProvisionText:
    provision_slot_id: str
    kc_entry_id: str
    doc_id: str
    section_number: str | None
    source_page: int | None
    verbatim_body: str
    frontmatter: dict[str, Any]
    gcs_uri: str
    sha256_ok: bool | None


@dataclass
class EvidenceItem:
    """Appended by the after_tool evidence ledger; drives citations and the viewer trace."""

    tool: str
    ref: str  # node id / provision_slot_id / kc_entry_id / job_id
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernanceIncident:
    """D5: emitted when an answer is blocked by governance. Sink = log now, Pub/Sub → BQ later."""

    incident_id: str
    occurred_at: str  # ISO-8601 UTC
    session_id: str
    user_id: str
    kc_entry_id: str
    provision_slot_id: str | None
    verdict: str
    chain: tuple[str, ...]
    question_sha256: str  # raw question is NOT shipped (PII minimisation)
