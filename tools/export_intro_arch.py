#!/usr/bin/env python3
"""Export the Studio 01 Intro figures → okf_veri_web/data/intro_arch.json (ADR 0015 · figure SSOT).

Where the figures come from
  - Hand-drawn figures: agents/design/graphrag_agent_v0.yaml `diagrams` (+ agents/design/rag_agent_v0.yaml for 3-4).
  - Figure 2-1 is NOT hand-drawn: it is generated from ontology/l1.yaml (classes · edges · layers) + live label counts.
  - «key» placeholders are filled at export time from live measurement (BigQuery · Dataplex · Cloud Storage),
    the local OKF build (okf/verification.json) or code constants read from the agent source.

Gates — any failure prints every problem, exits 1 and leaves the output file untouched:
  G1 measured  design `measured` block == live (per-label nodes/edges · totals · aliases · KC entries · GCS md · anchor aspect)
  G2 labels    deployed graph labels == ontology/l1.yaml; layout node/edge order == l1; l1 views exist; totals == Σ labels;
               KC anchors / glossary == l1; governance fixtures present; RAG corpus files == source PDFs
  G3 fill      every «key» resolves
  G4 tokens    identifiers in figure text (paths · file names · dotted · snake/UPPER_SNAKE · CamelCase · temp:keys)
               exist in figure.sources / ontology/l1.yaml / conventions.vocabulary
  G5 traps     2-3 panel checks match live edge_* rows; edges drawn in a panel are checked or in its CQ GQL
  G6 plane     Provision carries no governance columns (l1 properties + live view columns); listed columns exist
  G7 literals  no measured value ≥ 11 is typed by hand in figure text (use a «key»)
  G8 leak      output has no project id / project number / bucket / Spanner instance
  G9 hero      intro_tabs[].hero.example == the stored 06 report (okf_veri_web/data/eq_compare.json):
               question text · per-arm verdict · answer amount and every 억/만 amount in its steps appear in
               that arm's recorded answer (G7 skips KRW amounts for this reason)

Findings (reported, never fail): ontology/l1.yaml expected_rows / meta.counts vs live.

Usage (repo root):
  GOOGLE_API_USE_CLIENT_CERTIFICATE=false GOOGLE_API_USE_MTLS_ENDPOINT=never \\
  CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE=false \\
  uv run --no-project --with google-cloud-bigquery --with pyyaml python tools/export_intro_arch.py \\
      [--check-only] [--design-dir DIR]
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import html
import json
import os
import pathlib
import re
import sys
import urllib.parse

import yaml

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ.setdefault("GOOGLE_API_USE_MTLS_ENDPOINT", "never")

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import sync_gcs  # noqa: E402  BUCKET · PREFIX · fixture_objects
import verify_catalog as vc  # noqa: E402  PROJECT · PROJECT_NUMBER · LOCATION · ENTRY_GROUP · get_token · api_get

GRAPHRAG = ROOT / "finance" / "agents" / "starlight-graphrag"
RAG = ROOT / "finance" / "agents" / "starlight-rag-agent"
L1_PATH = ROOT / "finance" / "ontology" / "l1.yaml"
VERIFICATION = ROOT / "finance" / "okf" / "verification.json"
OUT = ROOT / "okf_veri_web" / "data" / "intro_arch.json"
EQ_REPORT = ROOT / "okf_veri_web" / "data" / "eq_compare.json"
DESIGN_FILES = ("graphrag_agent_v0.yaml", "rag_agent_v0.yaml")
ANCHOR_ASPECT = "ontology-class-anchors"

PLACE_RE = re.compile(r"«([a-z0-9_:]+)»")
FRONT_RE = re.compile(r"\A\s*---\n.*?\n---\n", re.S)
TAG_RE = re.compile(r"<[^>]+>")
EXT = r"(?:py|json|yaml|yml|md|html|js|css|sql|sh|toml)"
PATH_RE = re.compile(r"(?<![\w./-])((?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]*)", re.A)
FILE_RE = re.compile(rf"(?<![\w./-])([A-Za-z0-9_-]+\.{EXT})(?![\w.])", re.A)
TEMP_RE = re.compile(r"(?<![\w:])temp:[a-z_]+", re.A)
WILD_RE = re.compile(r"(?<![\w.])([a-z][a-z0-9_]*_)\*", re.A)
DOTTED_RE = re.compile(r"(?<![\w.])([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+)(?![\w.])", re.A)
SNAKE_RE = re.compile(r"(?<!\w)(_?[a-z][a-z0-9]*(?:_[a-z0-9]+)+)(?!\w)", re.A)
UPPER_RE = re.compile(r"(?<!\w)([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+)(?!\w)", re.A)
CAMEL_RE = re.compile(r"(?<![\w.])([A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+)(?!\w)", re.A)
KRW_RE = re.compile(r"\d{1,3}(?:,\d{3})*(?:억|만)")
NUM_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+|\d+)(?!\w|[.,]\d|%)", re.A)
IS_FLOWCHART = re.compile(r"\A\s*(?:---\n.*?\n---\n\s*)?flowchart\b", re.S)

STORE_LABEL = {
    "bigquery_native": "BigQuery",
    "bigquery_lex_plus_kc": "BigQuery + KC 거버넌스",
    "spanner_federated": "Spanner → BigQuery 연합",
}


class Fail(Exception):
    pass


HERO_META_KEYS = {"eq", "arm", "verdict"}  # identifiers / enums, not display text


def hero_texts(node, path: str = "hero") -> list[tuple[str, str]]:
    """Every display string in a hero block, with its path (meta keys excluded)."""
    if isinstance(node, str):
        return [(path, node)]
    if isinstance(node, list):
        return [t for i, x in enumerate(node) for t in hero_texts(x, f"{path}[{i}]")]
    if isinstance(node, dict):
        return [t for k, v in node.items() if k not in HERO_META_KEYS for t in hero_texts(v, f"{path}.{k}")]
    return []


def hero_map(node, fn):
    """Apply fn to every display string (meta keys kept as-is)."""
    if isinstance(node, str):
        return fn(node)
    if isinstance(node, list):
        return [hero_map(x, fn) for x in node]
    if isinstance(node, dict):
        return {k: (v if k in HERO_META_KEYS else hero_map(v, fn)) for k, v in node.items()}
    return node


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fmt(v) -> str:
    return f"{v:,}" if isinstance(v, int) else str(v)


def read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


# ----------------------------------------------------------------------------- code constants
def _one(pattern: str, text: str, what: str, flags: int = 0):
    found = re.findall(pattern, text, flags)
    if len(found) != 1:
        raise Fail(f"code constant `{what}`: expected exactly 1 match, found {len(found)}")
    return found[0]


def code_constants() -> dict:
    eng = read(GRAPHRAG / "app" / "orchestrator" / "engine.py")
    cfg = read(GRAPHRAG / "app" / "config.py")
    rag = read(RAG / "app" / "agent.py")
    c = {
        "cfg:tool_budget": int(_one(r'tool_budget: int = field\(default_factory=lambda: int\(_env\("STARLIGHT_TOOL_BUDGET", "(\d+)"\)\)\)', cfg, "tool_budget")),
        "cfg:max_graph_hops": int(_one(r'max_graph_hops: int = field\(default_factory=lambda: int\(_env\("STARLIGHT_MAX_GRAPH_HOPS", "(\d+)"\)\)\)', cfg, "max_graph_hops")),
        "cfg:max_gql_repairs": int(_one(r'max_gql_repairs: int = field\(default_factory=lambda: int\(_env\("STARLIGHT_MAX_GQL_REPAIRS", "(\d+)"\)\)\)', cfg, "max_gql_repairs")),
        "rag:top_k": int(_one(r'RAG_TOP_K = int\(os\.environ\.get\("STARLIGHT_RAG_TOP_K", "(\d+)"\)\)', rag, "RAG_TOP_K")),
        "planner:max_slots": int(_one(r"^_MAX_PLANNER_PROVISION_SLOTS = (\d+)", eng, "_MAX_PLANNER_PROVISION_SLOTS", re.M)),
        "cq:top_k": int(_one(r"_retrieve_top_gql_examples\(\s*query_text, requested_num, top_k=(\d+)\s*\)", eng, "top_k")),
    }
    _one(r"\[:_MAX_PLANNER_PROVISION_SLOTS\]", eng, "planner slot truncation")
    _one(r"max_repairs=rt\.settings\.max_gql_repairs", eng, "Step 1 loop uses cfg max_gql_repairs")
    full, exact = _one(
        r'is_exact_benchmark = \(best_score == (\d+)\) or \(\s*mode == "FULL_GRAPHRAG" and plan_matched_cq in '
        r"CQ_GQL_TEMPLATES and best_score >= (\d+)\s*\)", eng, "is_exact_benchmark")
    route = _one(r"\n    if best_score == (\d+):\n", eng, "template route")
    if route != full:
        raise Fail(f"engine.py: template route score {route} != is_exact_benchmark score {full}")
    c["cq:full_score"] = int(full)
    c["cq:exact_min_score"] = int(exact)
    return c


def cq_templates() -> dict:
    tree = ast.parse(read(GRAPHRAG / "app" / "orchestrator" / "engine.py"))
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign) else []
        if any(getattr(t, "id", None) == "CQ_GQL_TEMPLATES" for t in targets):
            return ast.literal_eval(node.value)
    raise Fail("engine.py: CQ_GQL_TEMPLATES not found")


def first_match_path(gql: str) -> str:
    for line in gql.splitlines():
        s = line.strip()
        if s.startswith("MATCH"):
            return s.rstrip().rstrip(",")
    raise Fail("CQ template has no MATCH line")


# ----------------------------------------------------------------------------- live measurement
def live_bigquery(l1: dict) -> dict:
    from google.cloud import bigquery

    client = bigquery.Client(project=vc.PROJECT)
    meta = l1["meta"]
    graph, ont, src = meta["property_graph_name"], meta["ontology_dataset"], meta["source_dataset"]

    def q(sql: str) -> list[dict]:
        return [dict(r.items()) for r in client.query(sql, location=vc.LOCATION).result()]

    def labels(match: str) -> dict:
        rows = q(f"SELECT l, COUNT(*) c FROM GRAPH_TABLE({graph} {match} COLUMNS (LABELS(x) AS ls)), UNNEST(ls) AS l GROUP BY l")
        return {r["l"]: int(r["c"]) for r in rows}

    nodes, edges = labels("MATCH (x)"), labels("MATCH ()-[x]->()")
    tot = q(f"SELECT (SELECT COUNT(*) FROM GRAPH_TABLE({graph} MATCH (x) COLUMNS (1 AS one))) n, "
            f"(SELECT COUNT(*) FROM GRAPH_TABLE({graph} MATCH ()-[x]->() COLUMNS (1 AS one))) e")[0]
    phys_sql = "\nUNION ALL\n".join(
        f"SELECT '{c['class_label']}' l, COUNT(*) c FROM `{vc.PROJECT}.{c['physical_table']}`" for c in l1["node_classes"])
    phys = {r["l"]: int(r["c"]) for r in q(phys_sql)}
    aliases = int(q(f"SELECT COUNT(*) c FROM `{vc.PROJECT}.{meta['alias_table']}`")[0]["c"])
    tables = q(f"SELECT 'ONT' ds, table_name, table_type FROM `{vc.PROJECT}.{ont}.INFORMATION_SCHEMA.TABLES` UNION ALL "
               f"SELECT 'SRC' ds, table_name, table_type FROM `{vc.PROJECT}.{src}.INFORMATION_SCHEMA.TABLES`")
    pv_view = next(c for c in l1["node_classes"] if c["class_label"] == "Provision")["graph_view"].split(".")[-1]
    cols = [r["column_name"] for r in q(
        f"SELECT column_name FROM `{vc.PROJECT}.{ont}.INFORMATION_SCHEMA.COLUMNS` WHERE table_name = '{pv_view}'")]
    o = f"`{vc.PROJECT}.{ont}"
    traps = q(f"""
WITH pv AS (SELECT provision_slot_id, doc_id, article_no, title FROM {o}.lex_provisions`)
SELECT 'HAS_EXCEPTION_PROVISO' AS edge, a.article_no AS src, b.article_no AS dst, b.doc_id AS dst_doc, e.exception_condition AS note, '' AS ctx, '' AS term
FROM {o}.edge_has_exception_proviso` e JOIN pv a ON a.provision_slot_id = e.base_slot_id JOIN pv b ON b.provision_slot_id = e.proviso_slot_id
UNION ALL
SELECT 'DELEGATES_TO_INTERNAL', a.article_no, b.article_no, b.doc_id, e.delegation_scope, '', ''
FROM {o}.edge_delegates_to_internal` e JOIN pv a ON a.provision_slot_id = e.external_slot_id JOIN pv b ON b.provision_slot_id = e.internal_slot_id
UNION ALL
SELECT 'CONFLICTS_BY_SECTOR', a.article_no, b.article_no, b.doc_id, e.conflict_warning, '', ''
FROM {o}.edge_conflicts_by_sector` e JOIN pv a ON a.provision_slot_id = e.bank_slot_id JOIN pv b ON b.provision_slot_id = e.distractor_slot_id
UNION ALL
SELECT 'INVOKES_PROVISION', e.context_id, b.article_no, b.doc_id, e.invocation_reason, e.context_id, e.term_key
FROM {o}.edge_invokes_provision` e JOIN pv b ON b.provision_slot_id = e.provision_slot_id""")
    return {"nodes": nodes, "edges": edges, "totals": {"nodes": int(tot["n"]), "edges": int(tot["e"])},
            "physical": phys, "aliases": aliases, "tables": tables, "provision_view": pv_view,
            "provision_view_columns": cols, "traps": traps}


def live_dataplex(l1: dict, token: str) -> dict:
    base = f"https://dataplex.googleapis.com/v1/projects/{vc.PROJECT}/locations/{vc.LOCATION}"
    entries, page = [], ""
    while True:
        data = vc.api_get(f"{base}/entryGroups/{vc.ENTRY_GROUP}/entries?pageSize=100" + (f"&pageToken={page}" if page else ""), token)
        entries += data.get("entries", [])
        page = data.get("nextPageToken", "")
        if not page:
            break
    ids = [e["name"].split("/entries/", 1)[1] for e in entries if not e["name"].endswith(f"/entries/{vc.ENTRY_GROUP}_entry")]
    fixtures = vc.fixture_entries()
    terms, page = [], ""
    while True:
        data = vc.api_get(f"{base}/glossaries/{l1['meta']['kc_glossary_id']}/terms?pageSize=100" + (f"&pageToken={page}" if page else ""), token)
        terms += data.get("terms", [])
        page = data.get("nextPageToken", "")
        if not page:
            break
    ont, graph = l1["meta"]["ontology_dataset"], l1["meta"]["property_graph_name"].split(".")[-1]
    entry = (f"{base}/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/{vc.PROJECT}/datasets/{ont}"
             f"/propertyGraphs/{graph}?view=CUSTOM&aspectTypes=projects/{vc.PROJECT}/locations/{vc.LOCATION}/aspectTypes/{ANCHOR_ASPECT}")
    aspect = vc.api_get(entry, token).get("aspects", {}).get(f"{vc.PROJECT_NUMBER}.{vc.LOCATION}.{ANCHOR_ASPECT}", {}).get("data", {})
    anchors = aspect.get("class_anchors") or []
    return {
        "entries": len(ids), "entries_fixture": len(fixtures & set(ids)), "fixtures_expected": len(fixtures),
        "glossary_terms": len(terms),
        "anchor_aspect": {
            "class_anchors": len(anchors),
            "key_bound_anchors": sum(1 for a in anchors if a.get("match_bind_key") and "$CANONICAL_ID" in str(a.get("gql_match_template", ""))),
            "ontology_version": aspect.get("ontology_version"),
            "keys": sorted(aspect),
            "class_labels": sorted(a.get("class_label", "") for a in anchors),
        },
    }


def live_rag_corpus(corpus: str, token: str) -> dict:
    """Files in the Vector RAG comparison corpus (agents/design/rag_agent_v0.yaml resources.rag_corpus)."""
    loc = corpus.split("/locations/", 1)[1].split("/", 1)[0]
    files, page = [], ""
    while True:
        data = vc.api_get(f"https://{loc}-aiplatform.googleapis.com/v1/{corpus}/ragFiles?pageSize=100"
                          + (f"&pageToken={page}" if page else ""), token)
        files += data.get("ragFiles", [])
        page = data.get("nextPageToken", "")
        if not page:
            break
    names = sorted(f.get("displayName", "") for f in files)
    return {"files": len(files), "pdf_files": sum(1 for n in names if n.lower().endswith(".pdf"))}


def live_gcs(token: str) -> dict:
    base = f"https://storage.googleapis.com/storage/v1/b/{sync_gcs.BUCKET}/o"
    names, page = [], ""
    while True:
        qs = {"prefix": f"{sync_gcs.PREFIX}/", "fields": "items(name),nextPageToken", "maxResults": "1000"}
        if page:
            qs["pageToken"] = page
        data = vc.api_get(base + "?" + urllib.parse.urlencode(qs), token)
        names += [i["name"] for i in data.get("items", [])]
        page = data.get("nextPageToken", "")
        if not page:
            break
    md = {n for n in names if n.endswith(".md")}
    fixtures = {f"{sync_gcs.PREFIX}/{f}" for f in sync_gcs.fixture_objects()}
    return {"objects": len(names), "md": len(md), "md_fixture": len(md & fixtures), "fixtures_expected": len(fixtures)}


# ----------------------------------------------------------------------------- token gate
class Resolver:
    """Answers "does this identifier exist?" against a figure's sources + l1 + vocabulary."""

    SCAN_DIRS = [(ROOT, False), (ROOT / "tools", False), (ROOT / "finance" / "data", False), (ROOT / "okf_veri_web", True),
                 (GRAPHRAG / "app", True), (RAG / "app", True)]
    TEXT_EXT = {".py", ".md", ".json", ".yaml", ".yml", ".sql", ".js", ".html"}

    def __init__(self, l1_text: str):
        self.l1_text = l1_text
        self.basenames: dict[str, pathlib.Path] = {}
        for d, recursive in self.SCAN_DIRS:
            for p in (d.rglob("*") if recursive else d.iterdir()):
                if p.is_file() and "__pycache__" not in p.parts and "node_modules" not in p.parts:
                    self.basenames.setdefault(p.name, p)
        self._cache: dict[tuple, str] = {}

    def source_text(self, sources: list[str]) -> tuple[str, list[str]]:
        key = tuple(sources)
        missing = []
        if key not in self._cache:
            parts = [self.l1_text]
            for s in sources:
                p = ROOT / s
                if not (p.is_dir() if s.endswith("/") else p.is_file()):
                    p = ROOT / "finance" / s
                if s.endswith("/"):
                    if not p.is_dir():
                        missing.append(s)
                        continue
                    parts += [read(f) for f in sorted(p.rglob("*"))
                              if f.is_file() and f.suffix in self.TEXT_EXT and "__pycache__" not in f.parts]
                elif p.is_file():
                    parts.append(read(p))
                else:
                    missing.append(s)
            self._cache[key] = "\n".join(parts)
        return self._cache[key], missing

    @staticmethod
    def path_exists(tok: str) -> bool:
        t = tok.rstrip("/")
        return bool(t) and ((ROOT / t).exists() or (ROOT / "finance" / t).exists() or (GRAPHRAG / t).exists())

    def file_exists(self, tok: str) -> bool:
        return tok in self.basenames or self.path_exists(tok)

    def check(self, text: str, sources: list[str], vocab: set[str], where: str) -> tuple[list[str], int]:
        src, missing = self.source_text(sources)
        errs = [f"{where}: source `{m}` does not exist" for m in missing]
        t = html.unescape(TAG_RE.sub(" ", FRONT_RE.sub("", text)))
        n = 0

        def blank(m: re.Match) -> str:
            return " " * len(m.group(0))

        def word(tok: str) -> bool:
            return re.search(rf"(?<!\w){re.escape(tok)}(?!\w)", src, re.A) is not None

        for m in PATH_RE.finditer(t):
            n += 1
            if not self.path_exists(m.group(1)):
                errs.append(f"{where}: path `{m.group(1)}` not found (repo root or agents/starlight-graphrag/)")
        t = PATH_RE.sub(blank, t)
        for m in FILE_RE.finditer(t):
            n += 1
            if not self.file_exists(m.group(1)):
                errs.append(f"{where}: file `{m.group(1)}` not found")
        t = FILE_RE.sub(blank, t)
        for m in TEMP_RE.finditer(t):
            n += 1
            if m.group(0) not in src:
                errs.append(f"{where}: state key `{m.group(0)}` not in sources")
        t = TEMP_RE.sub(blank, t)
        for m in WILD_RE.finditer(t):
            n += 1
            if not re.search(rf"(?<!\w){re.escape(m.group(1))}\w", src, re.A):
                errs.append(f"{where}: wildcard `{m.group(0)}` matches nothing in sources")
        t = WILD_RE.sub(blank, t)
        for m in DOTTED_RE.finditer(t):
            n += 1
            tok = m.group(1)
            if tok in src:
                continue
            mod, last = tok.split(".")[0], tok.split(".")[-1]
            f = self.basenames.get(mod + ".py")
            if not (f and re.search(rf"^\s*(?:async\s+)?def {re.escape(last)}\b|^\s*class {re.escape(last)}\b|^{re.escape(last)}\s*=", read(f), re.M)):
                errs.append(f"{where}: dotted `{tok}` not in sources and `{mod}.py` defines no `{last}`")
        t = DOTTED_RE.sub(blank, t)
        for rx in (SNAKE_RE, UPPER_RE):
            for m in rx.finditer(t):
                n += 1
                tok = m.group(1)
                if not (word(tok) or (tok + ".py") in self.basenames or (ROOT / tok).is_dir() or (ROOT / "finance" / tok).is_dir()):
                    errs.append(f"{where}: symbol `{tok}` not in sources / l1")
        for m in CAMEL_RE.finditer(t):
            n += 1
            tok = m.group(1)
            if tok not in vocab and not word(tok):
                errs.append(f"{where}: name `{tok}` not in sources / l1 / vocabulary")
        return errs, n


# ----------------------------------------------------------------------------- figure generation
def gen_l1_schema(fig: dict, l1: dict, live: dict) -> str:
    lay = fig["layout"]
    classes = {c["class_label"]: c for c in l1["node_classes"]}
    edges = {e["edge_label"]: e for e in l1["edge_definitions"]}
    if set(lay["node_order"]) != set(classes) or len(lay["node_order"]) != len(classes):
        raise Fail(f"2-1 layout.node_order != l1 node_classes: {sorted(set(lay['node_order']) ^ set(classes))}")
    if set(lay["edge_order"]) != set(edges) or len(lay["edge_order"]) != len(edges):
        raise Fail(f"2-1 layout.edge_order != l1 edge_definitions: {sorted(set(lay['edge_order']) ^ set(edges))}")
    grouped = [c for g in lay["groups"] for c in lay["node_order"] if classes[c]["layer"] == g["layer"]]
    if sorted(grouped) != sorted(classes):
        raise Fail("2-1 layout.groups do not cover every l1 class exactly once")
    ids = {c: f"n{i}" for i, c in enumerate(lay["node_order"])}
    cfg = lay.get("config") or {}
    out = ["---", "config:", "  flowchart:"] + [f"    {k}: {v}" for k, v in cfg.items()] + ["---", "flowchart TB"]
    for g in lay["groups"]:
        out.append(f'  subgraph {g["id"]}["{g["title"]}"]')
        for c in lay["node_order"]:
            if classes[c]["layer"] == g["layer"]:
                sep = " · " if c in lay.get("single_line", []) else "<br/>"
                out.append(f'    {ids[c]}["{c}{sep}{fmt(live["nodes"][c])}"]')
        out.append("  end")
    loops: dict[str, list[str]] = {}
    for el in lay["edge_order"]:
        e, cnt = edges[el], fmt(live["edges"][el])
        s, t = e["source_class"], e["target_class"]
        if s == t:
            loops.setdefault(s, []).append(f"{el} · {cnt}")
            continue
        extra = (lay.get("edge_label_extra") or {}).get(el)
        out.append(f'  {ids[s]} -->|"{el}<br/>{extra + " · " if extra else ""}{cnt}"| {ids[t]}')
    for s, labs in loops.items():
        out.append(f'  {ids[s]} -->|"{"<br/>".join(labs)}"| {ids[s]}')
    return "\n".join(out) + "\n"


def l1_physical_table(l1: dict, live: dict, order: list[str]) -> dict:
    classes = {c["class_label"]: c for c in l1["node_classes"]}
    rows = []
    for label in order:
        c = classes[label]
        rows.append({
            "class": label, "korean": c.get("korean_name", ""), "layer": c["layer"],
            "store": STORE_LABEL.get(c["source_plane"], c["source_plane"]),
            "physical_table": c["physical_table"], "graph_view": c["graph_view"].split(".")[-1],
            "rows_source": live["physical"][label], "nodes_graph": live["nodes"][label],
        })
    return {"columns": ["클래스", "저장소", "원천 테이블 → 노드 뷰", "행 (원천 · 그래프)"], "rows": rows}


# ----------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--check-only", action="store_true", help="run every gate, never write the output")
    ap.add_argument("--design-dir", default=str(ROOT / "finance" / "agents" / "design"), help="where the design YAMLs are (negative controls)")
    args = ap.parse_args()

    fails: list[str] = []
    gates: list[dict] = []

    def gate(gid: str, name: str, errs: list[str], checked: int) -> None:
        gates.append({"id": gid, "name": name, "ok": not errs, "checked": checked, "errors": len(errs)})
        fails.extend(f"[{gid}] {e}" for e in errs)

    design_dir = pathlib.Path(args.design_dir)
    designs = {f: yaml.safe_load((design_dir / f).read_text(encoding="utf-8")) for f in DESIGN_FILES}
    gr = designs["graphrag_agent_v0.yaml"]
    dg = gr["diagrams"]
    conv = dg["conventions"]
    figures: dict[str, dict] = {}
    for f in DESIGN_FILES:
        for fig in (designs[f].get("diagrams") or {}).get("figures") or []:
            if fig["id"] in figures:
                raise Fail(f"duplicate figure id {fig['id']}")
            figures[fig["id"]] = {**fig, "_design": f"agents/design/{f}"}
    l1_text = read(L1_PATH)
    l1 = yaml.safe_load(l1_text)
    ver = json.loads(read(VERIFICATION))

    # ---- measure
    t0 = utc_now()
    consts = code_constants()
    templates = cq_templates()
    live = live_bigquery(l1)
    token = vc.get_token()
    kc = live_dataplex(l1, token)
    gcs = live_gcs(token)
    rag = live_rag_corpus(designs["rag_agent_v0.yaml"]["resources"]["rag_corpus"]["resource_name"], token)
    t1 = utc_now()

    l1_nodes = [c["class_label"] for c in l1["node_classes"]]
    l1_edges = [e["edge_label"] for e in l1["edge_definitions"]]
    ldm = [c["class_label"] for c in l1["node_classes"] if c["layer"] == "LDM"]
    ont_tables = [(r["table_name"], r["table_type"]) for r in live["tables"] if r["ds"] == "ONT"]
    src_tables = [(r["table_name"], r["table_type"]) for r in live["tables"] if r["ds"] == "SRC"]
    values = {
        "pdf:count": int(ver["source_pdf_count"]),
        "rag:files": rag["files"],
        "okf:concepts": int(ver["total_concepts"]),
        "ledger:tables": len(ldm),
        "ledger:rows": sum(live["physical"][c] for c in ldm),
        "gcs:md": gcs["md"],
        "kc:entries": kc["entries"],
        "kc:anchors": kc["anchor_aspect"]["class_anchors"],
        "glossary:terms": kc["glossary_terms"],
        "l1:classes": len(l1_nodes),
        "l1:edges": len(l1_edges),
        "total:nodes": live["totals"]["nodes"],
        "total:edges": live["totals"]["edges"],
        "aliases": live["aliases"],
        "bq:v_node_views": sum(1 for n, t in ont_tables if t == "VIEW" and n.startswith("v_node_")),
        "bq:v_edge_views": sum(1 for n, t in ont_tables if t == "VIEW" and n.startswith("v_edge_")),
        "bq:edge_tables": sum(1 for n, t in ont_tables if t == "BASE TABLE" and n.startswith("edge_")),
        "bq:ont_views": sum(1 for n, t in src_tables if t == "VIEW" and n.startswith("ont_")),
        **consts,
    }

    # ---- G1 measured (design block == live)
    m = gr["measured"]
    errs, n = [], 0

    def same(label: str, want, got) -> None:
        nonlocal n
        n += 1
        if want != got:
            errs.append(f"measured.{label}: design {want!r} != live {got!r}")

    for lab in sorted(set(m["nodes"]) | set(live["nodes"])):
        same(f"nodes.{lab}", m["nodes"].get(lab), live["nodes"].get(lab))
    for lab in sorted(set(m["edges"]) | set(live["edges"])):
        same(f"edges.{lab}", m["edges"].get(lab), live["edges"].get(lab))
    same("totals.nodes", m["totals"]["nodes"], live["totals"]["nodes"])
    same("totals.edges", m["totals"]["edges"], live["totals"]["edges"])
    same("aliases", m["aliases"], live["aliases"])
    same("kc_okf_entries", m["kc_okf_entries"], kc["entries"])
    same("gcs_md_objects", m["gcs_md_objects"], gcs["md"])
    ka = m["kc_anchor_aspect"]
    same("kc_anchor_aspect.class_anchors", ka["class_anchors"], kc["anchor_aspect"]["class_anchors"])
    same("kc_anchor_aspect.key_bound_anchors", ka["key_bound_anchors"], kc["anchor_aspect"]["key_bound_anchors"])
    same("kc_anchor_aspect.ontology_version", str(ka["ontology_version"]), str(kc["anchor_aspect"]["ontology_version"]))
    same("kc_anchor_aspect.keys", sorted(ka["keys"]), kc["anchor_aspect"]["keys"])
    gate("G1", "design measured == live", errs, n)

    # ---- G2 labels / structure
    errs, n = [], 7
    if set(live["nodes"]) != set(l1_nodes):
        errs.append(f"node labels live≠l1: {sorted(set(live['nodes']) ^ set(l1_nodes))}")
    if set(live["edges"]) != set(l1_edges):
        errs.append(f"edge labels live≠l1: {sorted(set(live['edges']) ^ set(l1_edges))}")
    if sum(live["nodes"].values()) != live["totals"]["nodes"] or sum(live["edges"].values()) != live["totals"]["edges"]:
        errs.append(f"Σ label counts != element totals ({sum(live['nodes'].values())}/{live['totals']['nodes']} · "
                    f"{sum(live['edges'].values())}/{live['totals']['edges']})")
    views = {nm for nm, t in ont_tables if t == "VIEW"}
    missing_views = [c["graph_view"] for c in l1["node_classes"] if c["graph_view"].split(".")[-1] not in views]
    missing_views += [e["view_name"] for e in l1["edge_definitions"] if e["view_name"].split(".")[-1] not in views]
    if missing_views:
        errs.append(f"l1 views missing live: {missing_views}")
    if sorted(kc["anchor_aspect"]["class_labels"]) != sorted(l1_nodes):
        errs.append("KC anchor aspect class labels != l1 node classes")
    if kc["glossary_terms"] != len(l1.get("glossary_terms") or []):
        errs.append(f"live glossary terms {kc['glossary_terms']} != l1 glossary_terms {len(l1.get('glossary_terms') or [])}")
    if kc["entries_fixture"] != kc["fixtures_expected"] or gcs["md_fixture"] != gcs["fixtures_expected"]:
        errs.append(f"governance fixtures missing live (KC {kc['entries_fixture']}/{kc['fixtures_expected']} · "
                    f"GCS {gcs['md_fixture']}/{gcs['fixtures_expected']})")
    if rag["files"] != rag["pdf_files"] or rag["files"] != int(ver["source_pdf_count"]):
        errs.append(f"RAG corpus files {rag['files']} (pdf {rag['pdf_files']}) != source PDFs {ver['source_pdf_count']}")
    mermaid_l1: dict[str, str] = {}
    for fid, fig in figures.items():
        if fig["kind"] == "l1_schema":
            try:
                mermaid_l1[fid] = gen_l1_schema(fig, l1, live)
            except Fail as e:
                errs.append(str(e))
                mermaid_l1[fid] = ""
        if fig.get("node_order"):
            if set(fig["node_order"]) != set(l1_nodes) or len(fig["node_order"]) != len(l1_nodes):
                errs.append(f"{fid} node_order != l1 node_classes: {sorted(set(fig['node_order']) ^ set(l1_nodes))}")
    gate("G2", "graph labels · views · layout == ontology/l1.yaml", errs, n)

    # ---- G3 fill
    unresolved: set[str] = set()

    def fill(s: str) -> str:
        def rep(mm: re.Match) -> str:
            k = mm.group(1)
            if k not in values:
                unresolved.add(k)
                return mm.group(0)
            return fmt(values[k])
        return PLACE_RE.sub(rep, s or "")

    out_figs: dict[str, dict] = {}
    for fid, fig in figures.items():
        o = {"id": fid, "kind": fig["kind"], "title": fill(fig["title"]), "caption": fill(fig["caption"]),
             "sources": list(fig.get("sources") or []), "design": fig["_design"]}
        if fig["kind"] == "l1_schema":
            o["mermaid"] = mermaid_l1.get(fid, "")
            o["generated_from"] = "ontology/l1.yaml + live label counts"
        elif fig.get("mermaid"):
            o["mermaid"] = fill(fig["mermaid"])
        if fig.get("table") == "l1_physical":
            o["table"] = l1_physical_table(l1, live, fig.get("node_order") or l1_nodes)
        if fig["kind"] == "trap_paths":
            o["panels"] = []
            for p in fig["panels"]:
                if p["gql_from"] not in templates:
                    fails.append(f"[G5] {p['id']}: gql_from {p['gql_from']} not in CQ_GQL_TEMPLATES")
                    continue
                o["panels"].append({"id": p["id"], "title": fill(p["title"]), "text": fill(p["text"]),
                                    "mermaid": fill(p["mermaid"]), "gql_from": p["gql_from"],
                                    "gql": first_match_path(templates[p["gql_from"]]), "checks": len(p.get("checks") or []),
                                    "flowchart": bool(IS_FLOWCHART.match(p["mermaid"]))})
        if o.get("mermaid"):
            o["flowchart"] = bool(IS_FLOWCHART.match(o["mermaid"]))
        out_figs[fid] = o
    tabs = []
    for tab in dg["intro_tabs"]:
        ids = list(tab.get("figures") or []) + [x["figure"] for x in (tab.get("toggle") or {}).get("options", [])]
        for fid in ids:
            if fid not in out_figs:
                fails.append(f"[G3] tab {tab['id']}: figure {fid} not defined")
        t_out = {**{k: v for k, v in tab.items() if k not in ("lead", "hero")}, "lead": fill(tab.get("lead", ""))}
        if tab.get("hero"):
            t_out["hero"] = hero_map(tab["hero"], fill)
        tabs.append(t_out)
    gate("G3", "every «key» resolves", [f"placeholder «{k}» has no value" for k in sorted(unresolved)], len(values))

    # ---- G4 tokens
    res = Resolver(l1_text)
    vocab = set(conv.get("vocabulary") or [])
    errs, n = [], 0
    for fid, fig in figures.items():
        srcs = list(fig.get("sources") or [])
        texts = [("title", fig["title"]), ("caption", fig["caption"])]
        if fig["kind"] == "l1_schema":
            texts.append(("mermaid", mermaid_l1.get(fid, "")))
        elif fig.get("mermaid"):
            texts.append(("mermaid", fig["mermaid"]))
        for p in fig.get("panels") or []:
            texts += [(f"{p['id']}.title", p["title"]), (f"{p['id']}.text", p["text"]), (f"{p['id']}.mermaid", p["mermaid"])]
        for what, text in texts:
            e, k = res.check(PLACE_RE.sub(" ", text), srcs, vocab, f"{fid}.{what}")
            errs += e
            n += k
    for tab in dg["intro_tabs"]:
        e, k = res.check(PLACE_RE.sub(" ", tab.get("lead", "") + " " + tab.get("title", "")), [], vocab, f"tab {tab['id']}")
        errs += e
        n += k
        for where, text in hero_texts(tab.get("hero")):
            e, k = res.check(PLACE_RE.sub(" ", text), [], vocab, f"tab {tab['id']}.{where}")
            errs += e
            n += k
    gate("G4", "figure identifiers exist in sources / l1 / vocabulary", errs, n)

    # ---- G5 traps
    errs, n = [], 0
    l1_edge_set = set(l1_edges)
    for p in figures["2-3"]["panels"]:
        checked_edges = set()
        for c in p.get("checks") or []:
            n += 1
            checked_edges.add(c["edge"])
            hits = [r for r in live["traps"] if r["edge"] == c["edge"]
                    and ("ctx" not in c or r["ctx"] == c["ctx"]) and ("term" not in c or r["term"] == c["term"])
                    and ("src" not in c or r["src"] == c["src"]) and ("dst" not in c or r["dst"] == c["dst"])
                    and ("dst_doc" not in c or r["dst_doc"] == c["dst_doc"])
                    and all(s in (r["note"] or "") for s in c.get("contains") or [])]
            if not hits:
                errs.append(f"{p['id']}: no live row for {c}")
        gql = first_match_path(templates.get(p["gql_from"], "MATCH"))
        drawn = {t for t in UPPER_RE.findall(p["mermaid"]) if t in l1_edge_set}
        stray = drawn - checked_edges - set(UPPER_RE.findall(gql))
        if stray:
            errs.append(f"{p['id']}: edges drawn but neither checked nor in {p['gql_from']} GQL: {sorted(stray)}")
    gate("G5", "2-3 trap paths match live edge rows", errs, n)

    # ---- G6 plane invariant
    errs, n = [], 0
    plane_fig = next((f for f in figures.values() if f.get("plane_check")), figures.get("2-2") or figures.get("1-2") or {})
    pc = plane_fig.get("plane_check") or {}
    prov = next(c for c in l1["node_classes"] if c["class_label"] == "Provision")
    props = {p["name"] for p in prov.get("properties") or []}
    cols = set(live["provision_view_columns"])
    for col in pc.get("lacks") or []:
        n += 2
        if col in props:
            errs.append(f"l1 Provision has governance property `{col}`")
        if col in cols:
            errs.append(f"live {live['provision_view']} has governance column `{col}`")
    for col in pc.get("has") or []:
        n += 1
        if col not in cols:
            errs.append(f"live {live['provision_view']} lacks column `{col}` drawn in {plane_fig.get('id', '2-2')}")
    if not pc:
        errs.append("plane_check missing")
    gate("G6", "Provision node holds no governance columns", errs, n)

    # ---- G7 literals (raw figure text, before filling)
    measured_ints = set(values.values()) | set(live["nodes"].values()) | set(live["edges"].values()) | set(live["physical"].values())
    forbidden = {v for v in measured_ints if isinstance(v, int) and v >= 11}
    errs, n = [], 0
    raw_texts = []
    for fid, fig in figures.items():
        raw_texts += [(fid, fig["title"]), (fid, fig["caption"]), (fid, FRONT_RE.sub("", fig.get("mermaid") or ""))]
        for p in fig.get("panels") or []:
            raw_texts += [(p["id"], p["title"]), (p["id"], p["text"]), (p["id"], FRONT_RE.sub("", p["mermaid"]))]
    raw_texts += [(f"tab {t['id']}", t.get("lead", "")) for t in dg["intro_tabs"]]
    raw_texts += [(f"tab {t['id']}.{w}", x) for t in dg["intro_tabs"] for w, x in hero_texts(t.get("hero"))]
    for where, text in raw_texts:
        t = TAG_RE.sub(" ", text)
        for mm in NUM_RE.finditer(t):
            n += 1
            tok = mm.group(1)
            if (len(tok) > 1 and tok[0] == "0") or (mm.start() > 0 and t[mm.start() - 1] == "제"):
                continue
            if t[mm.end():mm.end() + 1] in ("억", "만", "원"):
                continue  # KRW amount (hero example), not a count — G9 ties it to the recorded 06 answer
            if int(tok.replace(",", "")) in forbidden:
                errs.append(f"{where}: literal {tok} equals a measured value — use a «key»")
    gate("G7", "no measured value typed by hand", errs, n)

    # ---- G9 hero example == stored 06 report
    errs, n = [], 0
    heroes = [(t["id"], t["hero"]) for t in dg["intro_tabs"] if t.get("hero")]
    if heroes:
        try:
            report = {q["id"]: q for q in json.loads(read(EQ_REPORT))["questions"]}
        except (OSError, ValueError, KeyError) as e:
            report = {}
            errs.append(f"cannot read {EQ_REPORT.relative_to(ROOT)}: {e}")
        norm = lambda x: re.sub(r"[*`\s]", "", x or "")
        for tid, hero in heroes:
            ex = hero.get("example")
            if not ex:
                continue
            n += 1
            q = report.get(ex.get("eq"))
            if q is None:
                errs.append(f"tab {tid}: example eq {ex.get('eq')!r} not in report")
                continue
            if ex.get("question") != q.get("question"):
                errs.append(f"tab {tid}: example question != report {ex['eq']} question")
            for a in ex.get("arms") or []:
                n += 2
                rec = q.get(a.get("arm")) or {}
                got = rec.get("verdict") or (rec.get("judge") or {}).get("verdict")
                if a.get("verdict") != got:
                    errs.append(f"tab {tid}: {ex['eq']} {a.get('arm')} verdict {a.get('verdict')!r} != report {got!r}")
                recorded = norm(rec.get("answer_markdown") or rec.get("answer"))
                if norm(a.get("answer")) not in recorded:
                    errs.append(f"tab {tid}: {ex['eq']} {a.get('arm')} answer {a.get('answer')!r} not in recorded answer")
                for amt in KRW_RE.findall(TAG_RE.sub(" ", " ".join(a.get("steps") or []))):
                    n += 1
                    if norm(amt) not in recorded:
                        errs.append(f"tab {tid}: {ex['eq']} {a.get('arm')} step amount {amt!r} not in recorded answer")
    gate("G9", "hero example == stored 06 report", errs, n)

    # ---- findings (never fail)
    findings = []
    for c in l1["node_classes"]:
        if c.get("expected_rows") is not None and c["expected_rows"] != live["nodes"].get(c["class_label"]):
            findings.append(f"ontology/l1.yaml {c['class_label']}.expected_rows {c['expected_rows']} != live {live['nodes'].get(c['class_label'])}")
    counts = l1["meta"].get("counts") or {}
    for key, livev in (("lex_provisions", live["nodes"].get("Provision")), ("lex_source_documents", live["nodes"].get("SourceDocument")),
                       ("lex_total_entries", int(ver["total_concepts"])), ("business_contexts", live["nodes"].get("BusinessContext"))):
        if key in counts and counts[key] != livev:
            findings.append(f"ontology/l1.yaml meta.counts.{key} {counts[key]} != measured {livev}")

    out = {
        "schema": "intro_arch/1",
        "generated_at": utc_now(),
        "measured": {"from": t0, "to": t1, "values": values,
                     "nodes": live["nodes"], "edges": live["edges"], "physical_rows": live["physical"],
                     "kc": {"entries": kc["entries"], "fixture_entries": kc["entries_fixture"], "glossary_terms": kc["glossary_terms"],
                            "anchor_aspect": {k: v for k, v in kc["anchor_aspect"].items() if k != "class_labels"}},
                     "gcs": gcs, "rag_corpus": rag},
        "conventions": {k: conv[k] for k in ("min_scale", "legend", "mermaid") if k in conv},
        "tabs": tabs,
        "figures": out_figs,
        "gates": gates,
        "findings": findings,
        "sources": {"design": [f"agents/design/{f}" for f in DESIGN_FILES], "l1": "ontology/l1.yaml",
                    "generator": "tools/export_intro_arch.py"},
    }

    # ---- G8 leak
    blob = json.dumps(out, ensure_ascii=False)
    spanner = re.search(r'SPANNER_INSTANCE = os\.environ\.get\("OKF_SPANNER_INSTANCE", "([^"]+)"\)', read(ROOT / "tools" / "setup_federation.py"))
    secrets = [vc.PROJECT, vc.PROJECT_NUMBER, sync_gcs.BUCKET] + ([spanner.group(1)] if spanner else [])
    leak_errs = [f"output contains `{s[:4]}…`" for s in secrets if s and s in blob]
    if not spanner:
        leak_errs.append("could not read SPANNER_INSTANCE from tools/setup_federation.py")
    gate("G8", "no project / bucket / instance ids in output", leak_errs, len(secrets))
    out["gates"] = gates

    # ---- report
    print(f"measured {t0} → {t1}")
    print("values: " + " · ".join(f"{k}={fmt(v)}" for k, v in values.items()))
    for g in gates:
        print(f"  {'PASS' if g['ok'] else 'FAIL'} {g['id']} {g['name']} (checked {g['checked']}, errors {g['errors']})")
    for f in findings:
        print(f"  FINDING {f}")
    if fails:
        for f in fails:
            print(f"  ✗ {f}")
        print(f"FAIL: {len(fails)} problem(s) — {OUT.relative_to(ROOT)} not written")
        return 1
    if args.check_only:
        print("OK (check-only): nothing written")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"OK wrote {OUT.relative_to(ROOT)} · figures {len(out_figs)} · tabs {len(tabs)}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Fail as e:
        print(f"FAIL: {e} — {OUT.relative_to(ROOT)} not written")
        sys.exit(1)
