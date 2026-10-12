"""Composition root for dependencies (adapters → services). The only place that picks
concrete implementations; tests build a Container from `tests/fakes` instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.adapters.bigquery import BigQueryAdapter
from app.adapters.dataplex import DataplexCatalogAdapter
from app.adapters.incident_sinks import LogIncidentSink, PubSubIncidentSink
from app.config import Settings, get_settings
from app.ports import AliasSourcePort, CatalogPort, GraphPort, IncidentSinkPort, ObjectRefPort, SqlPort
from app.services.governance import GovernanceService
from app.services.provision_reader import ProvisionReader


@dataclass(frozen=True)
class Container:
    settings: Settings
    graph: GraphPort
    sql: SqlPort
    objectref: ObjectRefPort
    aliases: AliasSourcePort
    catalog: CatalogPort
    incidents: IncidentSinkPort
    governance: GovernanceService
    provisions: ProvisionReader


def build(settings: Settings | None = None) -> Container:
    s = settings or get_settings()
    bq = BigQueryAdapter(s)
    kc = DataplexCatalogAdapter(s)
    sink: IncidentSinkPort = (
        PubSubIncidentSink(f"projects/{s.project}/topics/starlight-governance-incidents")
        if s.incident_sink == "pubsub"
        else LogIncidentSink()
    )
    return Container(
        settings=s,
        graph=bq,
        sql=bq,
        objectref=bq,
        aliases=bq,
        catalog=kc,
        incidents=sink,
        governance=GovernanceService(
            kc, okf_aspect_key=f"{s.project_number}.{s.data_location}.{s.okf_aspect_type}", max_hops=s.superseded_max_hops
        ),
        provisions=ProvisionReader(bq),
    )


@lru_cache(maxsize=1)
def get_container() -> Container:
    return build()
