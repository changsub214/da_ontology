"""Build the SchemaCard (prompt block) from the KC `ontology-class-anchors` aspect."""

from __future__ import annotations

import json
from typing import Any

from app.domain.models import ClassAnchor, SchemaCard


def from_aspect(data: dict[str, Any]) -> SchemaCard:
    """Parse the live aspect payload (keys measured 2026-09-27)."""
    anchors = tuple(
        ClassAnchor(
            class_label=a["class_label"],
            layer=a.get("layer", ""),
            primary_key=a.get("primary_key", ""),
            anchor_type=a.get("anchor_type", ""),
            gql_match_template=a.get("gql_match_template", ""),
        )
        for a in data.get("class_anchors", [])
    )
    raw_edges = data.get("edge_definitions_json") or "[]"
    edges = tuple(json.loads(raw_edges) if isinstance(raw_edges, str) else raw_edges)
    raw_terms = data.get("glossary_terms_json") or "[]"
    terms = tuple(json.loads(raw_terms) if isinstance(raw_terms, str) else raw_terms)
    return SchemaCard(
        graph_id=data.get("graph_id", ""),
        ontology_version=data.get("ontology_version", ""),
        governance_rule=data.get("governance_rule", ""),
        anchors=anchors,
        edges=edges,
        glossary_terms=terms,
    )


def render_prompt_block(card: SchemaCard) -> str:
    """Compact markdown the LLM reads: labels, anchor templates, edge directions, glossary keys."""
    lines: list[str] = [
        f"- Graph: `{card.graph_id}` (v{card.ontology_version})",
        f"- Governance Rule: {card.governance_rule}",
        "### Node Classes & Fixed KC GQL Templates (11)",
    ]
    for a in card.anchors:
        lines.append(
            f"- `:{a.class_label}` [{a.layer}] PK=`{a.primary_key}` ({a.anchor_type}) → `{a.gql_match_template}`"
        )
    lines.append("### Edge Views (15)")
    for e in card.edges:
        lbl = e.get("edge_label", "")
        src = e.get("source_class", e.get("src", ""))
        dst = e.get("target_class", e.get("dst", ""))
        desc = e.get("description", "")
        lines.append(f"- `(:{src})-[:{lbl}]->(:{dst})`: {desc}")
    if card.glossary_terms:
        lines.append("### Business Glossary Terms (`INVOKES_PROVISION.term_key`)")
        for t in card.glossary_terms:
            tk = t.get("term_key", t.get("id", ""))
            nm = t.get("display_name", t.get("name", ""))
            lines.append(f"- `{tk}` ({nm})")
    return "\n".join(lines)
