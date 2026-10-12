"""Ports (interfaces) between services and infrastructure.

Services depend only on these Protocols; `app/adapters/*` implement them against
BigQuery / Dataplex / HTTP / Pub/Sub; `tests/fakes` implement them in memory.
Replacing an adapter (e.g. log → Pub/Sub incident sink) never touches services.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.domain.models import GovernanceIncident, GqlDryRunResult


class GraphPort(Protocol):
    def dry_run_gql(self, gql: str) -> GqlDryRunResult:
        """Validate GQL syntax, schema labels/properties, and byte budget via BigQuery dry_run=True."""

    def run_gql(self, gql: str, *, max_rows: int) -> dict[str, Any]:
        """Execute a dry-run-validated read-only GQL statement; return {rows, job_id, bytes_processed}."""


class ObjectRefPort(Protocol):
    def signed_read_url(self, provision_slot_id: str) -> dict[str, Any]:
        """OBJ.GET_ACCESS_URL(gcs_obj_ref,'r') for one Provision node → {read_url, gcs_uri, kc_entry_id}."""

    def fetch(self, read_url: str) -> str:
        """HTTP GET the signed URL and return the OKF markdown text."""


class CatalogPort(Protocol):
    def get_graph_anchor_aspect(self) -> dict[str, Any]:
        """ontology-class-anchors aspect data attached to the finance_graph @bigquery entry."""

    def get_okf_entry(self, kc_entry_id: str) -> dict[str, Any] | None:
        """finance-okf entry (view=ALL) or None if not found."""

    def get_glossary_term(self, term_key: str) -> dict[str, Any] | None:
        """Business Glossary term by key."""


class AliasSourcePort(Protocol):
    def load_alias_rows(self) -> list[dict[str, Any]]:
        """All rows of starlight_bank_ontology.ont_entity_aliases."""


class IncidentSinkPort(Protocol):
    def emit(self, incident: GovernanceIncident) -> None:
        """Deliver a governance incident (D5). Must never raise into the agent turn."""
