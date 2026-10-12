"""Runtime Dependency Injection container for the Starlight GraphRAG agent.

Allows tools and callbacks (which ADK invokes as plain functions) to access the configured
ports & services, while enabling unit tests to swap in in-memory Fakes via `set_runtime()`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.adapters.bigquery import BigQueryAdapter
from app.adapters.dataplex import DataplexCatalogAdapter
from app.adapters.incident_sinks import LogIncidentSink
from app.config import Settings, get_settings
from app.domain.models import SchemaCard
from app.ports import (
    AliasSourcePort,
    CatalogPort,
    GraphPort,
    IncidentSinkPort,
    ObjectRefPort,
)
from app.services.governance import GovernanceService
from app.services.provision_reader import ProvisionReader
from app.services import schema_card as schema_card_svc


@dataclass
class RuntimeContainer:
    settings: Settings
    graph_port: GraphPort
    objectref_port: ObjectRefPort
    catalog_port: CatalogPort
    alias_port: AliasSourcePort
    incident_sink: IncidentSinkPort
    _cached_card: SchemaCard | None = field(default=None, init=False, repr=False)
    _cached_aliases: list[dict[str, Any]] | None = field(default=None, init=False, repr=False)

    @property
    def okf_aspect_key(self) -> str:
        return f"{self.settings.project_number}.{self.settings.data_location}.{self.settings.okf_aspect_type}"

    @property
    def governance_service(self) -> GovernanceService:
        return GovernanceService(
            self.catalog_port,
            okf_aspect_key=self.okf_aspect_key,
            max_hops=self.settings.superseded_max_hops,
        )

    @property
    def provision_reader(self) -> ProvisionReader:
        return ProvisionReader(self.objectref_port)

    def get_schema_card(self) -> SchemaCard:
        if self._cached_card is None:
            aspect_data = self.catalog_port.get_graph_anchor_aspect()
            self._cached_card = schema_card_svc.from_aspect(aspect_data)
        return self._cached_card

    def get_alias_rows(self) -> list[dict[str, Any]]:
        if self._cached_aliases is None:
            self._cached_aliases = self.alias_port.load_alias_rows()
        return self._cached_aliases


_ACTIVE_RUNTIME: RuntimeContainer | None = None


def get_runtime() -> RuntimeContainer:
    global _ACTIVE_RUNTIME
    if _ACTIVE_RUNTIME is None:
        s = get_settings()
        bq = BigQueryAdapter(s)
        dp = DataplexCatalogAdapter(s)
        sink = LogIncidentSink()
        _ACTIVE_RUNTIME = RuntimeContainer(
            settings=s,
            graph_port=bq,
            objectref_port=bq,
            catalog_port=dp,
            alias_port=bq,
            incident_sink=sink,
        )
    return _ACTIVE_RUNTIME


def set_runtime(rt: RuntimeContainer | None) -> None:
    """Override the runtime container (used by unit tests to inject Fakes)."""
    global _ACTIVE_RUNTIME
    _ACTIVE_RUNTIME = rt
