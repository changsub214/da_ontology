"""Dataplex Knowledge Catalog adapter (CatalogPort) — REST v1, ADC credentials (app/gcp_auth.py)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from app import gcp_auth
from app.config import Settings

_log = logging.getLogger(__name__)


class DataplexCatalogAdapter:
    def __init__(self, settings: Settings) -> None:
        self._s = settings

    def _bearer_token(self) -> str:
        # ADC with retries; gcloud only when installed (runbook S13 pitfall).
        return gcp_auth.access_token()

    def _get_json(self, url: str) -> dict[str, Any] | None:
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {self._bearer_token()}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            raise

    @property
    def okf_aspect_key(self) -> str:
        return f"{self._s.project_number}.{self._s.data_location}.{self._s.okf_aspect_type}"

    @property
    def anchor_aspect_key(self) -> str:
        return f"{self._s.project_number}.{self._s.data_location}.{self._s.anchor_aspect_type}"

    def get_graph_anchor_aspect(self) -> dict[str, Any]:
        """GET {graph_kc_entry}?view=CUSTOM&aspectTypes=.../ontology-class-anchors → aspect data."""
        aspect_type = f"{self._s.kc_parent}/aspectTypes/{self._s.anchor_aspect_type}"
        url = f"https://dataplex.googleapis.com/v1/{self._s.graph_kc_entry}?view=CUSTOM&aspectTypes={aspect_type}"
        entry = self._get_json(url)
        if entry is None:
            # Previously silent: an empty card skips GQL label checks (DR-07).
            _log.warning("graph KC entry not found (404): %s — schema card will be empty", self._s.graph_kc_entry)
            entry = {}
        aspects = entry.get("aspects") or {}
        if self.anchor_aspect_key in aspects:
            return aspects[self.anchor_aspect_key].get("data") or {}
        for k, v in aspects.items():
            if k.endswith(f".{self._s.anchor_aspect_type}"):
                return (v or {}).get("data") or {}
        return {}

    def get_okf_entry(self, kc_entry_id: str) -> dict[str, Any] | None:
        url = (
            f"https://dataplex.googleapis.com/v1/{self._s.kc_parent}"
            f"/entryGroups/{self._s.okf_entry_group}/entries/{kc_entry_id}?view=ALL"
        )
        return self._get_json(url)

    def get_glossary_term(self, term_key: str) -> dict[str, Any] | None:
        url = (
            f"https://dataplex.googleapis.com/v1/{self._s.kc_parent}"
            f"/glossaries/{self._s.glossary_id}/terms/{term_key}"
        )
        return self._get_json(url)
