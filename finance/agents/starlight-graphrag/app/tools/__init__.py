"""Tool registry for the unified Starlight GraphRAG agent.

All structured ledger queries (Spanner federated `ont_*` + BQ master tables) and graph traversals
are executed in a single unified GQL query (`graph_query` with BigQuery dry-run verification).
No separate `bigquery_sql` tool is used in GraphRAG (that belongs only to the RAG baseline arm).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.tools.fetch_provision import fetch_provision
from app.tools.graph_query import graph_query
from app.tools.kc_lookup import kc_lookup

GRAPHRAG_TOOLS: tuple[Callable[..., Any], ...] = (graph_query, kc_lookup, fetch_provision)
GRAPHRAG_TOOL_NAMES = tuple(t.__name__ for t in GRAPHRAG_TOOLS)

__all__ = ["GRAPHRAG_TOOLS", "GRAPHRAG_TOOL_NAMES"]
