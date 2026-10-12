"""Runtime settings for the Starlight GraphRAG agent.

All GCP identifiers live here (read from env / .env) so that no module hard-codes a
project, dataset, graph, connection or Dataplex resource. Swap environments by
changing env vars only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ.setdefault("GOOGLE_API_USE_MTLS_ENDPOINT", "never")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "finance-ontology-changseop")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


@dataclass(frozen=True)
class Settings:
    # --- GCP & Gemini Model --------------------------------------------------
    project: str = field(default_factory=lambda: _env("GOOGLE_CLOUD_PROJECT", "finance-ontology-changseop"))
    # Agent Runtime injects GOOGLE_CLOUD_PROJECT as the project *number* (reserved, not overridable).
    # Most APIs accept either, but IDs that embed the project as a literal string (the Dataplex
    # `@bigquery` entry ID) need the project *ID* — hence a separate env var (DR-07).
    project_id: str = field(default_factory=lambda: _env("STARLIGHT_PROJECT_ID", "finance-ontology-changseop"))
    project_number: str = field(default_factory=lambda: _env("STARLIGHT_PROJECT_NUMBER", "567090080191"))
    data_location: str = field(default_factory=lambda: _env("STARLIGHT_DATA_LOCATION", "us-central1"))
    model_name: str = field(default_factory=lambda: _env("STARLIGHT_MODEL", "gemini-3.8-flash"))
    model_location: str = field(default_factory=lambda: _env("GOOGLE_CLOUD_LOCATION", "global"))

    # --- BigQuery Graph plane (includes Spanner federated ont_* & ObjectRef) -
    ontology_dataset: str = field(default_factory=lambda: _env("STARLIGHT_ONTOLOGY_DATASET", "starlight_bank_ontology"))
    graph_name: str = field(default_factory=lambda: _env("STARLIGHT_GRAPH_NAME", "finance_graph"))
    alias_table: str = field(default_factory=lambda: _env("STARLIGHT_ALIAS_TABLE", "ont_entity_aliases"))
    objectref_connection: str = field(default_factory=lambda: _env("STARLIGHT_OBJECTREF_CONNECTION", "us-central1.okf-gcs-conn"))

    # --- Knowledge Catalog plane ---------------------------------------------
    okf_entry_group: str = field(default_factory=lambda: _env("STARLIGHT_OKF_ENTRY_GROUP", "finance-okf"))
    anchor_aspect_type: str = field(default_factory=lambda: _env("STARLIGHT_ANCHOR_ASPECT", "ontology-class-anchors"))
    okf_aspect_type: str = field(default_factory=lambda: _env("STARLIGHT_OKF_ASPECT", "okf"))
    glossary_id: str = field(default_factory=lambda: _env("STARLIGHT_GLOSSARY", "starlight-finance-glossary"))

    # --- Agent policy (Unified GraphRAG Agent — no product/eval_arm split) ---
    tool_budget: int = field(default_factory=lambda: int(_env("STARLIGHT_TOOL_BUDGET", "12")))
    max_graph_hops: int = field(default_factory=lambda: int(_env("STARLIGHT_MAX_GRAPH_HOPS", "12")))
    max_edge_patterns: int = field(default_factory=lambda: int(_env("STARLIGHT_MAX_EDGE_PATTERNS", "24")))
    max_rows: int = field(default_factory=lambda: int(_env("STARLIGHT_MAX_ROWS", "200")))
    max_bytes_billed: int = field(default_factory=lambda: int(_env("STARLIGHT_MAX_BYTES_BILLED", str(2 * 1024**3))))
    # Step 1 validate → repair loop: at most this many `_gemini_repair_gql` rounds before the turn is refused.
    # Validation (static + BigQuery dry-run) is not an execution; the GQL itself runs at most once (ADR 0016).
    max_gql_repairs: int = field(default_factory=lambda: int(_env("STARLIGHT_MAX_GQL_REPAIRS", "3")))
    superseded_max_hops: int = 3
    incident_sink: str = field(default_factory=lambda: _env("STARLIGHT_INCIDENT_SINK", "log"))  # log | pubsub (future)

    # --- Derived FQNs ---------------------------------------------------------
    @property
    def graph_fqn(self) -> str:
        return f"{self.ontology_dataset}.{self.graph_name}"

    @property
    def alias_table_fqn(self) -> str:
        return f"{self.project}.{self.ontology_dataset}.{self.alias_table}"

    @property
    def kc_parent(self) -> str:
        return f"projects/{self.project}/locations/{self.data_location}"

    @property
    def graph_kc_entry(self) -> str:
        # The `projects/{p}/locations/` prefix accepts the number; the entry ID after
        # `entries/` is an opaque string and only matches with the project ID (DR-07).
        return (
            f"{self.kc_parent}/entryGroups/@bigquery/entries/bigquery.googleapis.com/"
            f"projects/{self.project_id}/datasets/{self.ontology_dataset}/propertyGraphs/{self.graph_name}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
