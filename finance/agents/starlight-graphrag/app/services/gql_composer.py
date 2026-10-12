"""D2 Unified GQL Planner & Validator: KC anchor templates + GQL composition + BQ Dry-Run.

Pipeline
--------
1. Anchor (start node binding) → deterministic, from KC `gql_match_template`
   (e.g. "(c:Customer {customer_id: '$CANONICAL_ID'})") filled with pre-grounded ids.
2. Unified GQL Composition → composed by the GQL Planner over `starlight_bank_ontology.finance_graph`
   (supporting both `GRAPH starlight_bank_ontology.finance_graph MATCH ... RETURN ...` and
   `SELECT ... FROM GRAPH_TABLE(starlight_bank_ontology.finance_graph MATCH ... COLUMNS (...))`
   so structured Spanner/BQ ledgers, context rules, and ObjectRef signed URLs are queried in ONE shot).
3. Two-Stage Validation before execution:
   - Stage A (Static Policy): Must target `finance_graph`, read-only (no DML/DDL), only known
     11C/15E labels from `SchemaCard`, hop count ≤ `max_hops`, and `LIMIT` ≤ `max_rows`.
   - Stage B (BigQuery Dry-Run): `GraphPort.dry_run_gql(gql)` (`QueryJobConfig(dry_run=True)`)
     verifies GQL syntax, node/edge property names, types, and `total_bytes_processed` against
     live BigQuery before running the query.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from app.domain.models import ResolvedEntity, SchemaCard
from app.ports import GraphPort

PLACEHOLDER = "$CANONICAL_ID"

_FORBIDDEN_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|CALL|EXECUTE)\b",
    re.IGNORECASE,
)
_LABEL_PATTERN = re.compile(r"[\(:]\s*([A-Za-z_][A-Za-z0-9_]*)\b")
_EDGE_PATTERN = re.compile(r"\[:\s*([A-Za-z_][A-Za-z0-9_]*)\b")
_HOP_PATTERN = re.compile(r"-\s*\[[^\]]*\]\s*->|<-\s*\[[^\]]*\]\s*-")
_UNBOUNDED_QUANTIFIER = re.compile(r"\*\s*(?:\)|\]|$)|\b\d*\s*\.\.\s*([4-9]|\d{2,})\b")
_LIMIT_PATTERN = re.compile(r"\bLIMIT\s+(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class GqlValidation:
    ok: bool
    gql: str  # normalised statement when ok
    dry_run_bytes: int = 0
    errors: tuple[str, ...] = ()
    hints: tuple[str, ...] = ()


def render_anchor(template: str, canonical_id: str) -> str:
    """Fill one KC template with a resolved id (quotes escaped)."""
    return template.replace(PLACEHOLDER, canonical_id.replace("'", "\\'"))


def anchors_for(entities: list[ResolvedEntity], card: SchemaCard) -> list[str]:
    """Anchor MATCH snippets for the pre-grounded entities (offered to the GQL Planner)."""
    by_class = {a.class_label: a.gql_match_template for a in card.anchors}
    snippets: list[str] = []
    for ent in entities:
        tpl = by_class.get(ent.target_class)
        if tpl and PLACEHOLDER in tpl:
            snippets.append(render_anchor(tpl, ent.canonical_id))
        elif ent.gql_match_snippet:
            snippets.append(ent.gql_match_snippet)
    return snippets


def validate(
    gql: str,
    card: SchemaCard,
    *,
    graph_fqn: str,
    max_hops: int = 12,
    max_edge_patterns: int = 24,
    max_rows: int = 200,
    max_bytes_billed: int = 2 * 1024**3,
    graph_port: GraphPort | None = None,
) -> GqlValidation:
    """Static checks + optional BigQuery dry-run (`dry_run=True`) verification."""
    stmt = (gql or "").strip().rstrip(";")
    errors: list[str] = []
    hints: list[str] = []

    if not stmt:
        return GqlValidation(ok=False, gql="", errors=("Empty GQL statement.",))

    # 1. Read-only check
    m_kw = _FORBIDDEN_KEYWORDS.search(stmt)
    if m_kw:
        errors.append(f"Forbidden DDL/DML keyword `{m_kw.group(1).upper()}` in GQL.")

    # 2. Must target the property graph via GRAPH <fqn> or GRAPH_TABLE(<fqn>
    upper = stmt.upper()
    graph_fqn_upper = graph_fqn.upper()
    graph_short_upper = graph_fqn.split(".")[-1].upper()
    has_graph_prefix = upper.startswith(f"GRAPH {graph_fqn_upper}") or upper.startswith(
        f"GRAPH {graph_short_upper}"
    )
    has_graph_table = "GRAPH_TABLE(" in upper and (
        graph_fqn_upper in upper or graph_short_upper in upper
    )
    if not (has_graph_prefix or has_graph_table):
        errors.append(
            f"Query must use `GRAPH {graph_fqn} MATCH ...` or `SELECT ... FROM GRAPH_TABLE({graph_fqn} MATCH ...)`."
        )
        hints.append(
            f"Start with `GRAPH {graph_fqn}` or wrap traversal in `GRAPH_TABLE({graph_fqn} MATCH ... COLUMNS (...))`."
        )

    # 3. Check edge labels against SchemaCard (15 edges)
    known_edges = card.edge_labels
    if known_edges:
        for edge_lbl in _EDGE_PATTERN.findall(stmt):
            if edge_lbl not in known_edges:
                errors.append(f"Unknown edge label `{edge_lbl}` (not in KC schema card).")
                hints.append(f"Allowed edge labels: {', '.join(sorted(known_edges))}")

    # 4. Check node labels in `(var:Label` patterns against SchemaCard (11 classes)
    known_nodes = card.node_labels
    if known_nodes:
        for node_lbl in re.findall(r"\(\s*[A-Za-z0-9_]*\s*:\s*([A-Za-z_][A-Za-z0-9_]*)", stmt):
            if node_lbl not in known_nodes:
                errors.append(f"Unknown node label `{node_lbl}` (not in KC schema card).")
                hints.append(f"Allowed node labels: {', '.join(sorted(known_nodes))}")

    # 5. Guard against unbounded Kleene star & check linear chain (<=8) / total star branches (<=16)
    if _UNBOUNDED_QUANTIFIER.search(stmt):
        errors.append("Unbounded or >3-hop quantified path (`*`) is forbidden on self-referential edges.")
    clauses = re.split(r",|\bOPTIONAL\s+MATCH\b|\bMATCH\b|\bWHERE\b|\bRETURN\b|\bCOLUMNS\b", stmt, flags=re.IGNORECASE)
    longest_chain = max((len(_HOP_PATTERN.findall(c)) for c in clauses), default=0)
    total_edges = len(_HOP_PATTERN.findall(stmt))
    if longest_chain > max_hops:
        errors.append(f"Linear chain has {longest_chain} hops, exceeding max_hops={max_hops}.")
    if total_edges > max_edge_patterns:
        errors.append(f"Query has {total_edges} total edge patterns across branches, exceeding max_edge_patterns={max_edge_patterns}.")

    # 6. Enforce LIMIT <= max_rows
    m_lim = _LIMIT_PATTERN.search(stmt)
    if m_lim:
        lim_val = int(m_lim.group(1))
        if lim_val > max_rows:
            errors.append(f"LIMIT {lim_val} exceeds max_rows={max_rows}.")
    else:
        stmt = f"{stmt}\nLIMIT {max_rows}"

    if errors:
        return GqlValidation(ok=False, gql=stmt, errors=tuple(errors), hints=tuple(hints))

    # 7. Stage B: BigQuery Dry-Run Validation (when GraphPort is wired)
    dry_bytes = 0
    if graph_port is not None:
        dry = graph_port.dry_run_gql(stmt)
        dry_bytes = dry.total_bytes_processed
        if not dry.ok:
            return GqlValidation(
                ok=False,
                gql=stmt,
                dry_run_bytes=dry_bytes,
                errors=dry.errors or ("BigQuery GQL dry-run failed.",),
                hints=("Check property names and GQL RETURN/COLUMNS expressions against the KC schema card.",),
            )
        if dry_bytes > max_bytes_billed:
            return GqlValidation(
                ok=False,
                gql=stmt,
                dry_run_bytes=dry_bytes,
                errors=(f"Dry-run bytes {dry_bytes} exceed max_bytes_billed={max_bytes_billed}.",),
            )

    return GqlValidation(ok=True, gql=stmt, dry_run_bytes=dry_bytes)
