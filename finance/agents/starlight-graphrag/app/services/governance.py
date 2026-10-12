"""KC-only governance: status / superseded_by chain → Verdict (ADR 0005 single source).

Rule (F2, aligned with KC `governance_rule`): ALLOW when status ∈ {stable, verified};
deprecated → follow superseded_by up to `max_hops`; no valid replacement → BLOCKED.
Reference implementation: tools/kc_aspect_loader.py::resolve_kc_provision.
"""

from __future__ import annotations

import json
from typing import Any

from app.domain.models import KcVerdict, Verdict
from app.ports import CatalogPort

READABLE_STATUSES = frozenset({"stable", "verified"})


class GovernanceService:
    def __init__(self, catalog: CatalogPort, *, okf_aspect_key: str, max_hops: int = 3) -> None:
        self._catalog = catalog
        self._okf_aspect_key = okf_aspect_key
        self._max_hops = max_hops

    def _extract_okf_aspect(self, entry: dict[str, Any]) -> dict[str, Any]:
        aspects = entry.get("aspects") or {}
        if self._okf_aspect_key in aspects:
            return aspects[self._okf_aspect_key].get("data") or {}
        for k, v in aspects.items():
            if k.endswith(".okf") or k == "okf":
                return (v or {}).get("data") or {}
        return entry.get("okf_data") or {}

    def resolve(self, kc_entry_id: str) -> KcVerdict:
        visited: list[str] = []
        curr_id = (kc_entry_id or "").strip()
        if not curr_id:
            return KcVerdict(
                requested_entry_id=kc_entry_id,
                verdict=Verdict.BLOCKED_NOT_FOUND,
                reason="Empty kc_entry_id.",
            )

        for depth in range(self._max_hops + 1):
            visited.append(curr_id)
            entry = self._catalog.get_okf_entry(curr_id)
            if not entry:
                return KcVerdict(
                    requested_entry_id=kc_entry_id,
                    verdict=Verdict.BLOCKED_NOT_FOUND,
                    chain=tuple(visited),
                    reason=f"KC Entry `{curr_id}` not found in Knowledge Catalog.",
                )

            okf_data = self._extract_okf_aspect(entry)
            status = str(okf_data.get("status", "unknown")).strip()
            version = str(okf_data.get("version", "0.2.0")).strip()
            gcs_uri = str(entry.get("entrySource", {}).get("resource", "") or okf_data.get("gcs_uri", "")).strip()

            if status in READABLE_STATUSES:
                return KcVerdict(
                    requested_entry_id=kc_entry_id,
                    verdict=Verdict.ALLOW if depth == 0 else Verdict.SUPERSEDED_RESOLVED,
                    active_entry_id=curr_id,
                    status=status,
                    version=version,
                    chain=tuple(visited),
                    gcs_uri=gcs_uri or None,
                )

            # Follow superseded_by chain when deprecated
            next_id = ""
            extra_raw = okf_data.get("extra", "")
            if extra_raw:
                try:
                    if isinstance(extra_raw, str) and extra_raw.strip().startswith("{"):
                        extra_obj = json.loads(extra_raw)
                        next_id = str(extra_obj.get("superseded_by", "")).strip()
                    elif isinstance(extra_raw, dict):
                        next_id = str(extra_raw.get("superseded_by", "")).strip()
                    elif isinstance(extra_raw, list):
                        for item in extra_raw:
                            if (
                                isinstance(item, list)
                                and len(item) == 2
                                and item[0] in (["superseded_by"], "superseded_by")
                            ):
                                next_id = str(item[1] or "").strip()
                                break
                except Exception:
                    pass
            if not next_id:
                next_id = str(okf_data.get("superseded_by", "")).strip()
            if " (" in next_id:
                next_id = next_id.split(" (", 1)[0].strip()

            if not next_id or next_id in visited:
                return KcVerdict(
                    requested_entry_id=kc_entry_id,
                    verdict=Verdict.BLOCKED_DEPRECATED,
                    active_entry_id=None,
                    status=status,
                    version=version,
                    chain=tuple(visited),
                    gcs_uri=gcs_uri or None,
                    reason=f"KC Entry `{curr_id}` is `{status}` with no valid `superseded_by` target.",
                )
            curr_id = next_id

        return KcVerdict(
            requested_entry_id=kc_entry_id,
            verdict=Verdict.BLOCKED_MAX_DEPTH_EXCEEDED,
            chain=tuple(visited),
            reason=f"Superseded chain exceeded max_hops={self._max_hops}.",
        )
