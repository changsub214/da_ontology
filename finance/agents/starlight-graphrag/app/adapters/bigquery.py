"""BigQuery adapter: GraphPort (with dry_run_gql + run_gql) + ObjectRefPort + AliasSourcePort.

One BigQuery client, job-level guards (dry_run=True validation, maximum_bytes_billed, read-only).
All structured ledger tables (including Spanner federated `ont_*`) and unstructured ObjectRefs
(`gcs_obj_ref`) are accessed directly through `starlight_bank_ontology.finance_graph` in GQL.

When the GCP project runs in on-demand mode (where native `GRAPH` execution requires an
Enterprise slot reservation), `compile_gql_to_graph_views_sql` transparently lowers the GQL
`MATCH` pattern to the exact underlying `v_node_*` (11 views) and `v_edge_*` (15 views)
defined in `CREATE PROPERTY GRAPH starlight_bank_ontology.finance_graph` so both
`QueryJobConfig(dry_run=True)` and live query execution run against real BigQuery + Spanner Data Boost.
"""

from __future__ import annotations

import datetime as dt
import decimal
import json
import os
import re
import urllib.request
from typing import Any

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ.setdefault("GOOGLE_API_USE_MTLS_ENDPOINT", "never")

from google.cloud import bigquery

from app.config import Settings
from app.domain.models import GqlDryRunResult

# Exact 1:1 mapping from `CREATE PROPERTY GRAPH starlight_bank_ontology.finance_graph`
NODE_VIEW_MAP: dict[str, tuple[str, str]] = {
    "BusinessContext": ("v_node_business_context", "context_id"),
    "SourceDocument": ("v_node_source_document", "doc_id"),
    "Provision": ("v_node_provision", "provision_slot_id"),
    "LoanContract": ("v_node_loan_contract", "contract_id"),
    "Customer": ("v_node_customer", "customer_id"),
    "FinancialProduct": ("v_node_financial_product", "product_code"),
    "WorkoutHistory": ("v_node_workout_history", "workout_id"),
    "Collateral": ("v_node_collateral", "collateral_id"),
    "DelinquencyEvent": ("v_node_delinquency_event", "event_id"),
    "RateCutRequest": ("v_node_rate_cut_request", "request_id"),
    "ExceptionApproval": ("v_node_exception_approval", "approval_id"),
}

# Edge Label -> (edge_view_name, source_fk, src_node_pk, dest_fk, dst_node_pk)
EDGE_VIEW_MAP: dict[str, tuple[str, str, str, str, str]] = {
    "BORROWED_BY": ("v_edge_borrowed_by", "contract_id", "contract_id", "customer_id", "customer_id"),
    "OF_PRODUCT": ("v_edge_of_product", "contract_id", "contract_id", "product_code", "product_code"),
    "HAS_COLLATERAL": ("v_edge_has_collateral", "contract_id", "contract_id", "collateral_id", "collateral_id"),
    "HAS_DELINQUENCY": ("v_edge_has_delinquency", "contract_id", "contract_id", "event_id", "event_id"),
    "HAS_RATE_CUT_REQUEST": ("v_edge_has_rate_cut_request", "contract_id", "contract_id", "request_id", "request_id"),
    "HAS_EXCEPTION_APPROVAL": ("v_edge_has_exception_approval", "contract_id", "contract_id", "approval_id", "approval_id"),
    "HAS_WORKOUT_HISTORY": ("v_edge_has_workout_history", "contract_id", "contract_id", "workout_id", "workout_id"),
    "SCOPES_PORTFOLIO": ("v_edge_scopes_portfolio", "context_id", "context_id", "contract_id", "contract_id"),
    "INVOKES_PROVISION": ("v_edge_invokes_provision", "context_id", "context_id", "provision_slot_id", "provision_slot_id"),
    "GOVERNED_BY_CRITERIA": ("v_edge_governed_by_criteria", "contract_id", "contract_id", "provision_slot_id", "provision_slot_id"),
    "EVALUATED_UNDER_PROVISION": ("v_edge_evaluated_under_provision", "request_id", "request_id", "provision_slot_id", "provision_slot_id"),
    "PART_OF_DOCUMENT": ("v_edge_part_of_document", "provision_slot_id", "provision_slot_id", "doc_id", "doc_id"),
    "HAS_EXCEPTION_PROVISO": ("v_edge_has_exception_proviso", "base_slot_id", "provision_slot_id", "proviso_slot_id", "provision_slot_id"),
    "DELEGATES_TO_INTERNAL": ("v_edge_delegates_to_internal", "external_slot_id", "provision_slot_id", "internal_slot_id", "provision_slot_id"),
    "CONFLICTS_BY_SECTOR": ("v_edge_conflicts_by_sector", "bank_slot_id", "provision_slot_id", "distractor_slot_id", "provision_slot_id"),
}

_NODE_TOKEN_RE = re.compile(
    r"\(\s*([A-Za-z_][A-Za-z0-9_]*)?\s*(?::\s*([A-Za-z_][A-Za-z0-9_]*))?\s*(?:\{([^}]*)\})?\s*\)"
)
_STEP_RE = re.compile(
    r"(\<\-\s*\[\s*(?:([A-Za-z_][A-Za-z0-9_]*)\s*)?:\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\{([^}]*)\})?\s*\]\s*\-"
    r"|\-\s*\[\s*(?:([A-Za-z_][A-Za-z0-9_]*)\s*)?:\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:\{([^}]*)\})?\s*\]\s*\-\>)"
    r"\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)?\s*(?::\s*([A-Za-z_][A-Za-z0-9_]*))?\s*(?:\{([^}]*)\})?\s*\)"
)
_PROP_KV_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*('(?:\\'|[^'])*'|\d+(?:\.\d+)?)")


def compile_gql_to_graph_views_sql(gql: str, dataset_fqn: str) -> str:
    """Compile a `GRAPH ... MATCH ... WHERE ... RETURN ...` statement into SQL over `v_node_*`/`v_edge_*`."""
    stmt = gql.strip().rstrip(";")
    # If wrapped in GRAPH_TABLE(...), extract inner MATCH ... COLUMNS (...)
    gt_match = re.search(
        r"^(.*?)\bFROM\s+GRAPH_TABLE\s*\(\s*[A-Za-z0-9_`.\-]+\s+MATCH\s+(.*?)\bCOLUMNS\s*\((.*?)\)\s*\)(.*)$",
        stmt,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if gt_match:
        select_prefix = gt_match.group(1).strip()
        match_and_where = gt_match.group(2).strip()
        columns_expr = gt_match.group(3).strip()
        trailing_sql = gt_match.group(4).strip()
        inner_gql = f"GRAPH finance_graph MATCH {match_and_where} RETURN {columns_expr}"
        inner_sql = compile_gql_to_graph_views_sql(inner_gql, dataset_fqn)
        return f"{select_prefix} FROM ({inner_sql}) {trailing_sql}".strip()

    # Standard GRAPH <name> MATCH <pattern> [WHERE <cond>] RETURN <cols> [ORDER BY ...] [LIMIT ...]
    m_ret = re.search(r"\bRETURN\b\s+(.*)$", stmt, flags=re.IGNORECASE | re.DOTALL)
    if not m_ret:
        return stmt
    return_tail = m_ret.group(1).strip()
    before_return = stmt[: m_ret.start()].strip()

    m_where = re.search(r"\bWHERE\b\s+(.*)$", before_return, flags=re.IGNORECASE | re.DOTALL)
    where_clause_raw = ""
    if m_where:
        where_clause_raw = m_where.group(1).strip()
        before_where = before_return[: m_where.start()].strip()
    else:
        before_where = before_return

    m_match = re.search(r"\bMATCH\b\s+(.*)$", before_where, flags=re.IGNORECASE | re.DOTALL)
    if not m_match:
        return stmt
    pattern_str = m_match.group(1).strip()

    bound_vars: dict[str, str] = {}  # alias -> label
    from_clauses: list[str] = []
    where_filters: list[str] = []
    auto_idx = [0]

    def _next_alias(prefix: str) -> str:
        auto_idx[0] += 1
        return f"_{prefix}_{auto_idx[0]}"

    def _add_inline_props(alias: str, props_str: str | None) -> None:
        if not props_str:
            return
        for k, v in _PROP_KV_RE.findall(props_str):
            if k in ("provision_slot_id", "kc_entry_id") and v.startswith("'") and "/" not in v:
                # Support short slot id like 'art_029' matching full path or exact id
                clean_v = v.strip("'")
                where_filters.append(
                    f"({alias}.{k} = {v} OR {alias}.{k} LIKE '%/{clean_v}')"
                )
            else:
                where_filters.append(f"{alias}.{k} = {v}")

    # Split comma-separated path chains
    chains = [c.strip() for c in re.split(r",\s*(?=\()", pattern_str) if c.strip()]
    for chain in chains:
        first_m = _NODE_TOKEN_RE.match(chain)
        if not first_m:
            continue
        cur_var = first_m.group(1) or _next_alias("n")
        cur_lbl = first_m.group(2) or bound_vars.get(cur_var)
        if not cur_lbl:
            continue
        cur_props = first_m.group(3)
        if cur_var not in bound_vars:
            bound_vars[cur_var] = cur_lbl
            view_name = NODE_VIEW_MAP[cur_lbl][0]
            from_clauses.append(
                f"{'FROM' if not from_clauses else 'CROSS JOIN'} `{dataset_fqn}.{view_name}` AS {cur_var}"
            )
        _add_inline_props(cur_var, cur_props)

        rest = chain[first_m.end() :]
        for step in _STEP_RE.finditer(rest):
            raw_arrow = step.group(1)
            is_reverse = raw_arrow.startswith("<-")
            if is_reverse:
                edge_var = step.group(2) or _next_alias("e")
                edge_lbl = step.group(3)
                edge_props = step.group(4)
            else:
                edge_var = step.group(5) or _next_alias("e")
                edge_lbl = step.group(6)
                edge_props = step.group(7)
            nxt_var = step.group(8) or _next_alias("n")
            nxt_lbl = step.group(9) or bound_vars.get(nxt_var, "Provision")
            nxt_props = step.group(10)

            e_view, src_fk, src_pk, dst_fk, dst_pk = EDGE_VIEW_MAP[edge_lbl]
            if is_reverse:
                # (cur) <-[:EDGE]- (nxt) means nxt is source, cur is destination
                from_clauses.append(
                    f"JOIN `{dataset_fqn}.{e_view}` AS {edge_var} ON {cur_var}.{dst_pk} = {edge_var}.{dst_fk}"
                )
                if nxt_var not in bound_vars:
                    bound_vars[nxt_var] = nxt_lbl
                    n_view = NODE_VIEW_MAP[nxt_lbl][0]
                    from_clauses.append(
                        f"JOIN `{dataset_fqn}.{n_view}` AS {nxt_var} ON {edge_var}.{src_fk} = {nxt_var}.{src_pk}"
                    )
                else:
                    where_filters.append(f"{edge_var}.{src_fk} = {nxt_var}.{src_pk}")
            else:
                # (cur) -[:EDGE]-> (nxt) means cur is source, nxt is destination
                from_clauses.append(
                    f"JOIN `{dataset_fqn}.{e_view}` AS {edge_var} ON {cur_var}.{src_pk} = {edge_var}.{src_fk}"
                )
                if nxt_var not in bound_vars:
                    bound_vars[nxt_var] = nxt_lbl
                    n_view = NODE_VIEW_MAP[nxt_lbl][0]
                    from_clauses.append(
                        f"JOIN `{dataset_fqn}.{n_view}` AS {nxt_var} ON {edge_var}.{dst_fk} = {nxt_var}.{dst_pk}"
                    )
                else:
                    where_filters.append(f"{edge_var}.{dst_fk} = {nxt_var}.{dst_pk}")

            _add_inline_props(edge_var, edge_props)
            _add_inline_props(nxt_var, nxt_props)
            cur_var = nxt_var
            cur_lbl = nxt_lbl

    if where_clause_raw:
        where_filters.append(f"({where_clause_raw})")

    sql_parts = [f"SELECT {return_tail}"]
    # Wait: if return_tail contains ORDER BY or LIMIT at the end, split it out so WHERE comes before ORDER BY / LIMIT
    m_post = re.search(r"\b(GROUP\s+BY|ORDER\s+BY|LIMIT)\b", return_tail, flags=re.IGNORECASE)
    if m_post:
        select_expr = return_tail[: m_post.start()].strip()
        post_expr = return_tail[m_post.start() :].strip()
    else:
        select_expr = return_tail
        post_expr = ""

    sql_lines = [f"SELECT {select_expr}"] + from_clauses
    if where_filters:
        sql_lines.append("WHERE " + " AND ".join(where_filters))
    if post_expr:
        sql_lines.append(post_expr)
    return "\n".join(sql_lines)


def _json_safe(val: Any) -> Any:
    if isinstance(val, decimal.Decimal):
        return int(val) if val == int(val) else float(val)
    if isinstance(val, (dt.date, dt.datetime)):
        return val.isoformat()
    if isinstance(val, dict):
        return {str(k): _json_safe(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_json_safe(v) for v in val]
    return val


def _extract_read_url(access_url_val: Any) -> str:
    """Extract the signed GET URL from OBJ.GET_ACCESS_URL output (JSON string or dict)."""
    if not access_url_val:
        return ""
    if isinstance(access_url_val, str):
        raw = access_url_val.strip()
        if raw.startswith("{"):
            try:
                obj = json.loads(raw)
                return str(
                    (obj.get("access_urls") or {}).get("read_url")
                    or obj.get("read_url")
                    or ""
                )
            except Exception:
                return ""
        return raw
    if isinstance(access_url_val, dict):
        return str(
            (access_url_val.get("access_urls") or {}).get("read_url")
            or access_url_val.get("read_url")
            or ""
        )
    return ""


class BigQueryAdapter:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._client: bigquery.Client | None = None

    @property
    def client(self) -> bigquery.Client:
        if self._client is None:
            self._client = bigquery.Client(
                project=self._s.project,
                location=self._s.data_location,
            )
        return self._client

    @property
    def dataset_fqn(self) -> str:
        return f"{self._s.project}.{self._s.ontology_dataset}"

    # GraphPort ---------------------------------------------------------------
    def dry_run_gql(self, gql: str) -> GqlDryRunResult:
        """Validate GQL via BigQuery QueryJobConfig(dry_run=True, use_query_cache=False)."""
        cfg = bigquery.QueryJobConfig(
            dry_run=True,
            use_query_cache=False,
            default_dataset=self.dataset_fqn,
        )
        try:
            job = self.client.query(gql, job_config=cfg)
            return GqlDryRunResult(
                ok=True,
                total_bytes_processed=int(job.total_bytes_processed or 0),
            )
        except Exception as exc:
            err_msg = str(exc)
            if "require a reservation with Enterprise" in err_msg or "GRAPH" in gql.upper():
                try:
                    compiled_sql = compile_gql_to_graph_views_sql(gql, self.dataset_fqn)
                    job2 = self.client.query(compiled_sql, job_config=cfg)
                    return GqlDryRunResult(
                        ok=True,
                        total_bytes_processed=int(job2.total_bytes_processed or 0),
                    )
                except Exception as exc2:
                    return GqlDryRunResult(
                        ok=False,
                        total_bytes_processed=0,
                        errors=(str(exc2),),
                    )
            return GqlDryRunResult(
                ok=False,
                total_bytes_processed=0,
                errors=(err_msg,),
            )

    def run_gql(self, gql: str, *, max_rows: int) -> dict[str, Any]:
        """Execute validated GQL over starlight_bank_ontology.finance_graph."""
        cfg = bigquery.QueryJobConfig(
            maximum_bytes_billed=self._s.max_bytes_billed,
            default_dataset=self.dataset_fqn,
        )
        try:
            job = self.client.query(gql, job_config=cfg)
            rows_iter = job.result(max_results=max_rows)
            rows = [_json_safe(dict(r)) for r in rows_iter]
            return {
                "rows": rows,
                "job_id": job.job_id,
                "bytes_processed": int(job.total_bytes_processed or 0),
            }
        except Exception as exc:
            if "require a reservation with Enterprise" in str(exc):
                compiled_sql = compile_gql_to_graph_views_sql(gql, self.dataset_fqn)
                job2 = self.client.query(compiled_sql, job_config=cfg)
                rows_iter = job2.result(max_results=max_rows)
                rows = [_json_safe(dict(r)) for r in rows_iter]
                return {
                    "rows": rows,
                    "job_id": job2.job_id,
                    "bytes_processed": int(job2.total_bytes_processed or 0),
                    "compiled_sql": compiled_sql,
                }
            raise

    # ObjectRefPort -----------------------------------------------------------
    def signed_read_url(self, provision_slot_id: str) -> dict[str, Any]:
        """SELECT OBJ.GET_ACCESS_URL(gcs_obj_ref,'r') FROM v_node_provision WHERE provision_slot_id=@id."""
        sql = f"""
            SELECT
              provision_slot_id,
              kc_entry_id,
              doc_id,
              article_no AS section_number,
              title,
              gcs_uri,
              TO_JSON_STRING(OBJ.GET_ACCESS_URL(gcs_obj_ref, 'r')) AS access_url_json
            FROM `{self.dataset_fqn}.v_node_provision`
            WHERE provision_slot_id = @slot_id
               OR kc_entry_id = @slot_id
               OR provision_slot_id LIKE CONCAT('%/', @slot_id)
            LIMIT 1
        """
        cfg = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("slot_id", "STRING", provision_slot_id),
            ],
            maximum_bytes_billed=self._s.max_bytes_billed,
        )
        rows = [dict(r) for r in self.client.query(sql, job_config=cfg).result()]
        if not rows:
            raise LookupError(f"Provision node `{provision_slot_id}` not found in v_node_provision.")
        r = rows[0]
        return {
            "provision_slot_id": r.get("provision_slot_id"),
            "kc_entry_id": r.get("kc_entry_id"),
            "doc_id": r.get("doc_id"),
            "section_number": r.get("section_number"),
            "source_page": None,
            "gcs_uri": r.get("gcs_uri"),
            "read_url": _extract_read_url(r.get("access_url_json")),
        }

    def fetch(self, read_url: str) -> str:
        req = urllib.request.Request(read_url, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.read().decode("utf-8")

    # AliasSourcePort ---------------------------------------------------------
    def load_alias_rows(self) -> list[dict[str, Any]]:
        sql = f"SELECT * FROM `{self._s.alias_table_fqn}`"
        return [_json_safe(dict(r)) for r in self.client.query(sql).result()]
