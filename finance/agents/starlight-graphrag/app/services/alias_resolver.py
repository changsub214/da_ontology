"""D3 pre-grounding: longest-match-first alias resolution over ont_entity_aliases.

Ported from tools/kc_aspect_loader.py::resolve_query_aliases_longest_match (verified
2026-09-26). Pure function → runs inside a callback in microseconds, no LLM round trip.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.domain.models import ResolvedEntity

MIN_ALIAS_LEN = 2


def resolve(query: str, alias_rows: Iterable[dict[str, Any]]) -> list[ResolvedEntity]:
    """Return non-overlapping alias spans, longest alias first, ordered by position.

    Prevents short prefixes (e.g. '별빛') from shadowing longer specific spans
    (e.g. '별빛 프라임 중견기업 운전자금').
    """
    rows = sorted(alias_rows, key=lambda r: len(r["alias_term"]), reverse=True)
    occupied: list[tuple[int, int]] = []
    out: list[ResolvedEntity] = []
    for r in rows:
        term = r["alias_term"]
        if len(term) < MIN_ALIAS_LEN:
            continue
        start = query.find(term)
        if start == -1:
            continue
        end = start + len(term)
        if any(not (end <= s or start >= e) for s, e in occupied):
            continue
        occupied.append((start, end))
        out.append(
            ResolvedEntity(
                span=(start, end),
                alias_term=term,
                target_class=r["target_class"],
                match_bind_key=r["match_bind_key"],
                canonical_id=r["canonical_id"],
                canonical_display=r["canonical_display"],
                gql_match_snippet=r["gql_match_snippet"],
            )
        )
    out.sort(key=lambda m: m.span[0])
    return out
