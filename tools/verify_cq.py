#!/usr/bin/env python3
"""verify_cq.py — Competency Question 게이트 (ontology/cq/competency_questions.yaml)

CQ 는 OKF 번들이 아니라 **원본 PDF**(data/un_data/*.pdf) 와 **라이브 저장소**
(BigQuery `starlight_bank` 의 마스터 3종 + Spanner 연합 뷰 `ont_*` 5종 — Data Boost 경유)
에 동시에 근거해야 한다. 이 스크립트는 그 주장을 실패 가능한 방식으로 측정한다.

Gates
  CQ-G1 quote      : evidence.quote 가 선언된 PDF·쪽 원문에 (공백 제거 후) 그대로 존재
  CQ-G2 columns    : data_fields 의 테이블·컬럼이 라이브 스키마에 실재
                     (source_store=spanner 면 Spanner INFORMATION_SCHEMA 와 BQ ont_* 뷰 양쪽)
  CQ-G3 queries    : answer_queries 가 라이브에서 실행되고 expect 를 만족
  CQ-G4 triangle   : business_context + 규범 근거(binding|internal) ≥1 + data_fields ≥1
  CQ-G5 no-leakage : 쿼리가 계산한 파생 컬럼명이 저장소 물리 컬럼으로 존재하지 않음
                     (정답이 원장에 미리 계산돼 들어가 있지 않음)
   CQ-G6 coverage     : 테마 배분 · PDF 10종 · 테이블 8종 커버리지
  CQ-G7 parity       : BQ 연합 뷰(ont_*) 행수 == Spanner 직조회 행수
  CQ-G8 graph_labels : graph_path 의 모든 노드(:Class)·엣지([:EDGE]) 라벨이 ontology/l1.yaml 의 11 Classes · 15 Edges 에 정합

Usage
  python tools/verify_cq.py                      # 전 게이트 실행 → ontology/cq/cq_report.json
  python tools/verify_cq.py --measure            # 쿼리 결과만 출력 (expect 작성용)
  python tools/verify_cq.py --negative-control   # 고의 결함 4종 주입 → 각각 FAIL 나는지 확인
"""
from __future__ import annotations

import argparse, copy, datetime as dt, decimal, json, os, re, subprocess, sys, unicodedata

import yaml

os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
os.environ["GOOGLE_API_USE_MTLS_ENDPOINT"] = "never"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CQ_FILE = os.path.join(ROOT, "finance", "ontology", "cq", "competency_questions.yaml")
L1_FILE = os.path.join(ROOT, "finance", "ontology", "l1.yaml")
REPORT = os.path.join(ROOT, "finance", "ontology", "cq", "cq_report.json")
PDF_DIR = os.path.join(ROOT, "finance", "data", "un_data")

PROJECT = os.environ.get("OKF_PROJECT", "finance-ontology-changseop")
DATASET = os.environ.get("OKF_BQ_DATASET", "starlight_bank")
SPANNER_INSTANCE = os.environ.get("OKF_SPANNER_INSTANCE", "finance-cs")
SPANNER_DB = os.environ.get("OKF_SPANNER_DATABASE", "starlight_bank")
DS = f"`{PROJECT}.{DATASET}`"
SPANNER_TABLES = ["loan_contracts", "collaterals", "delinquency_events",
                  "rate_cut_requests", "exception_approvals"]


def configure_domain(domain: str) -> None:
    global CQ_FILE, L1_FILE, REPORT, PDF_DIR, DATASET, SPANNER_DB, DS, SPANNER_TABLES
    _pdf_cache.clear()
    if domain == "ecommerce":
        CQ_FILE = os.path.join(ROOT, "ecommerce", "ontology", "cq", "competency_questions.yaml")
        L1_FILE = os.path.join(ROOT, "ecommerce", "ontology", "l1.yaml")
        REPORT = os.path.join(ROOT, "ecommerce", "ontology", "cq", "cq_report.json")
        PDF_DIR = os.path.join(ROOT, "ecommerce", "data", "un_data")
        DATASET = "kmarket_ecommerce"
        SPANNER_DB = "kmarket_ecommerce"
        DS = f"`{PROJECT}.{DATASET}`"
        SPANNER_TABLES = ["orders", "order_items", "inventory_items", "events", "campaign_exceptions"]
    else:
        CQ_FILE = os.path.join(ROOT, "finance", "ontology", "cq", "competency_questions.yaml")
        L1_FILE = os.path.join(ROOT, "finance", "ontology", "l1.yaml")
        REPORT = os.path.join(ROOT, "finance", "ontology", "cq", "cq_report.json")
        PDF_DIR = os.path.join(ROOT, "finance", "data", "un_data")
        DATASET = os.environ.get("OKF_BQ_DATASET", "starlight_bank")
        SPANNER_DB = os.environ.get("OKF_SPANNER_DATABASE", "starlight_bank")
        DS = f"`{PROJECT}.{DATASET}`"
        SPANNER_TABLES = ["loan_contracts", "collaterals", "delinquency_events",
                          "rate_cut_requests", "exception_approvals"]


# ---------------------------------------------------------------------------
# PDF text (per page, two extraction modes, whitespace-free + NFC)
# ---------------------------------------------------------------------------
_norm_ws = re.compile(r"\s+")


def norm(s: str) -> str:
    return _norm_ws.sub("", unicodedata.normalize("NFKC", s))


_pdf_cache: dict[str, list[tuple[str, ...]]] = {}


def pdf_pages(filename: str) -> list[tuple[str, ...]]:
    if filename not in _pdf_cache:
        path = os.path.join(PDF_DIR, filename)
        out = []
        for mode in (["-layout"], ["-raw"], []):
            txt = subprocess.run(["pdftotext", *mode, path, "-"], capture_output=True,
                                 text=True, check=True).stdout
            out.append([norm(p) for p in txt.split("\f")])
        _pdf_cache[filename] = list(zip(*out))
    return _pdf_cache[filename]


def quote_found(filename: str, page: int, quote: str) -> tuple[bool, list[int]]:
    """Return (found on declared page, pages where found)."""
    pages = pdf_pages(filename)
    q = norm(quote)
    hits = [i + 1 for i, modes in enumerate(pages) if any(q in m for m in modes)]
    return page in hits, hits


# ---------------------------------------------------------------------------
# Live stores
# ---------------------------------------------------------------------------
_bq = None


def bq():
    global _bq
    if _bq is None:
        from google.cloud import bigquery
        _bq = bigquery.Client(project=PROJECT, location="us-central1")
    return _bq


def run_sql(sql: str) -> tuple[list[str], list[dict]]:
    job = bq().query(sql.replace("{ds}", DS))
    res = job.result()
    cols = [f.name for f in res.schema]
    rows = []
    for r in res:
        d = {}
        for k, v in r.items():
            if isinstance(v, decimal.Decimal):
                v = float(v)
            elif isinstance(v, (dt.date, dt.datetime)):
                v = v.isoformat()
            d[k] = v
        rows.append(d)
    return cols, rows


def bq_schema() -> dict[str, set[str]]:
    _, rows = run_sql(f"SELECT table_name, column_name FROM {DS}.INFORMATION_SCHEMA.COLUMNS")
    out: dict[str, set[str]] = {}
    for r in rows:
        out.setdefault(r["table_name"], set()).add(r["column_name"])
    return out


def spanner_db():
    from google.cloud import spanner
    return spanner.Client(project=PROJECT).instance(SPANNER_INSTANCE).database(SPANNER_DB)


def spanner_schema_and_counts() -> tuple[dict[str, set[str]], dict[str, int]]:
    db = spanner_db()
    schema: dict[str, set[str]] = {}
    counts: dict[str, int] = {}
    with db.snapshot(multi_use=True) as s:
        for t, c in s.execute_sql(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = ''"):
            schema.setdefault(t, set()).add(c)
        for t in SPANNER_TABLES:
            counts[t] = list(s.execute_sql(f"SELECT COUNT(*) FROM {t}"))[0][0]
    return schema, counts


# ---------------------------------------------------------------------------
# Expectation operators
# ---------------------------------------------------------------------------

def _eq(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))
    return a == b


def check_expect(expect: dict, cols: list[str], rows: list[dict]) -> list[str]:
    errs = []
    if "exact_rows" in expect and len(rows) != expect["exact_rows"]:
        errs.append(f"exact_rows: got {len(rows)} want {expect['exact_rows']}")
    if "min_rows" in expect and len(rows) < expect["min_rows"]:
        errs.append(f"min_rows: got {len(rows)} want >= {expect['min_rows']}")
    for want in expect.get("must_contain", []):
        if not any(all(_eq(r.get(k), v) for k, v in want.items()) for r in rows):
            errs.append(f"must_contain: no row matches {want}")
    for want in expect.get("must_not_contain", []):
        if any(all(_eq(r.get(k), v) for k, v in want.items()) for r in rows):
            errs.append(f"must_not_contain: a row matches {want}")
    for k, v in expect.get("sum", {}).items():
        got = sum((r.get(k) or 0) for r in rows)
        if not _eq(got, v):
            errs.append(f"sum({k}): got {got} want {v}")
    for k, v in expect.get("all_rows_equal", {}).items():
        bad = [r for r in rows if not _eq(r.get(k), v)]
        if bad:
            errs.append(f"all_rows_equal({k}={v}): {len(bad)} rows differ")
    if "scalar" in expect:
        if len(rows) != 1:
            errs.append(f"scalar: expected 1 row, got {len(rows)}")
        else:
            for k, v in expect["scalar"].items():
                if not _eq(rows[0].get(k), v):
                    errs.append(f"scalar({k}): got {rows[0].get(k)} want {v}")
    for k in expect.get("must_be_null", []):
        if any(r.get(k) is not None for r in rows):
            errs.append(f"must_be_null({k}): non-null present")
    return errs


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------
NORMATIVE = {"binding", "internal"}


def gate_quotes(doc, sources):
    res = []
    for cq in doc["cqs"]:
        for ev in cq["evidence"]:
            fn = sources[ev["doc"]]["file"]
            ok, hits = quote_found(fn, ev["page"], ev["quote"])
            res.append({"cq": cq["id"], "doc": ev["doc"], "page": ev["page"], "ok": ok,
                        "found_on_pages": hits, "quote": ev["quote"][:60]})
    return res


def gate_columns(doc, bqs, sps):
    res = []
    for cq in doc["cqs"]:
        for f in cq["data_fields"]:
            t = f["table"]
            missing = [c for c in f["columns"] if c not in bqs.get(t, set())]
            if f.get("source_store") == "spanner":
                base = t.removeprefix("ont_")
                missing += [f"spanner:{base}.{c}" for c in f["columns"]
                            if c not in sps.get(base, set())]
            res.append({"cq": cq["id"], "table": t, "ok": not missing, "missing": missing})
    return res


def gate_queries(doc, measure=False):
    res, measured = [], {}
    for cq in doc["cqs"]:
        for i, q in enumerate(cq["answer_queries"]):
            key = f"{cq['id']}#{i + 1}"
            try:
                cols, rows = run_sql(q["sql"])
            except Exception as e:  # noqa: BLE001
                res.append({"cq": key, "ok": False, "errors": [f"SQL error: {e}"[:400]]})
                continue
            measured[key] = {"columns": cols, "rows": rows}
            errs = [] if measure else check_expect(q.get("expect", {}), cols, rows)
            res.append({"cq": key, "ok": not errs, "errors": errs, "row_count": len(rows),
                        "columns": cols})
    return res, measured


def gate_triangle(doc):
    res = []
    for cq in doc["cqs"]:
        errs = []
        if not cq.get("business_context", {}).get("id"):
            errs.append("no business_context")
        if not any(ev["authority"] in NORMATIVE for ev in cq["evidence"]):
            errs.append("no normative (binding|internal) evidence")
        if not cq.get("data_fields"):
            errs.append("no data_fields")
        res.append({"cq": cq["id"], "ok": not errs, "errors": errs})
    return res


def gate_leakage(doc, bqs, sps, qres):
    physical = set().union(*bqs.values(), *sps.values())
    declared = {c for cq in doc["cqs"] for f in cq["data_fields"] for c in f["columns"]}
    leaks = []
    for r in qres:
        for c in r.get("columns", []):
            if c not in declared and c in physical:
                # derived answer column exists physically somewhere → leakage suspect
                leaks.append({"cq": r["cq"], "column": c})
    # precomputed-answer columns must not exist physically in either store
    forbidden = re.compile(r"(min_prov|required_prov|expected_|golden|scenario|governing_pdf|"
                           r"_ratio$|npl_90d|ews_30d|delinq_1m|clause|exempt)", re.I)
    for c in sorted(physical):
        if forbidden.search(c) and c != "debt_ratio_pct":
            leaks.append({"cq": "*", "physical_column": c})
    return [{"ok": not leaks, "leaks": leaks}]


def gate_coverage(doc, sources):
    want = doc["meta"]["theme_allocation"]
    got: dict[str, int] = {}
    for cq in doc["cqs"]:
        got[cq["theme"]] = got.get(cq["theme"], 0) + 1
    docs_used = {ev["doc"] for cq in doc["cqs"] for ev in cq["evidence"]}
    tables_used = {f["table"] for cq in doc["cqs"] for f in cq["data_fields"]}
    all_tables = set(doc["meta"]["required_tables"])
    errs = []
    if got != want:
        errs.append(f"theme allocation {got} != {want}")
    if len(doc["cqs"]) != 20:
        errs.append(f"cq count {len(doc['cqs'])} != 20")
    if docs_used != set(sources):
        errs.append(f"pdf not used: {sorted(set(sources) - docs_used)}")
    if not all_tables <= tables_used:
        errs.append(f"tables not used: {sorted(all_tables - tables_used)}")
    ids = [cq["id"] for cq in doc["cqs"]]
    if len(ids) != len(set(ids)):
        errs.append("duplicate ids")
    return [{"ok": not errs, "errors": errs, "themes": got, "pdfs_used": len(docs_used),
             "tables_used": sorted(tables_used)}]


def gate_parity(bqs_counts, sp_counts):
    res = []
    for t in SPANNER_TABLES:
        res.append({"table": t, "bq_ont": bqs_counts[t], "spanner": sp_counts[t],
                    "ok": bqs_counts[t] == sp_counts[t]})
    return res


def gate_graph_labels(doc):
    l1 = yaml.safe_load(open(L1_FILE, encoding="utf-8"))
    valid_nodes = {n["class_label"] for n in l1["node_classes"]}
    valid_edges = {e["edge_label"] for e in l1["edge_definitions"]}
    res = []
    for cq in doc["cqs"]:
        gp = cq.get("graph_path", "")
        node_labels = re.findall(r"\(\s*[A-Za-z0-9_]*\s*:\s*([A-Za-z_][A-Za-z0-9_]*)", gp)
        edge_labels = re.findall(r"\[\s*[A-Za-z0-9_]*\s*:\s*([A-Z_][A-Z0-9_]*)", gp)
        bad_nodes = [n for n in node_labels if n not in valid_nodes]
        bad_edges = [e for e in edge_labels if e not in valid_edges]
        status = cq.get("graph_status")
        ok = (
            bool(node_labels)
            and bool(edge_labels)
            and not bad_nodes
            and not bad_edges
            and status == "aligned_l1_v1.2"
        )
        res.append({
            "cq": cq["id"],
            "ok": ok,
            "nodes": node_labels,
            "edges": edge_labels,
            "bad_nodes": bad_nodes,
            "bad_edges": bad_edges,
            "graph_status": status,
        })
    return res


def run_all(doc, *, live=None, verbose=True):
    sources = doc["sources"]
    if live is None:
        bqs = bq_schema()
        sps, sp_counts = spanner_schema_and_counts()
        ont_counts = {t: run_sql(f"SELECT COUNT(*) n FROM {DS}.ont_{t}")[1][0]["n"]
                      for t in SPANNER_TABLES}
        live = (bqs, sps, sp_counts, ont_counts)
    bqs, sps, sp_counts, ont_counts = live
    g = {}
    g["CQ-G1_quote"] = gate_quotes(doc, sources)
    g["CQ-G2_columns"] = gate_columns(doc, bqs, sps)
    qres, measured = gate_queries(doc)
    g["CQ-G3_queries"] = qres
    g["CQ-G4_triangle"] = gate_triangle(doc)
    g["CQ-G5_no_leakage"] = gate_leakage(doc, bqs, sps, qres)
    g["CQ-G6_coverage"] = gate_coverage(doc, sources)
    g["CQ-G7_parity"] = gate_parity(ont_counts, sp_counts)
    g["CQ-G8_graph_labels"] = gate_graph_labels(doc)
    summary = {k: {"pass": sum(1 for r in v if r["ok"]), "total": len(v)} for k, v in g.items()}
    ok = all(s["pass"] == s["total"] for s in summary.values())
    if verbose:
        for k, s in summary.items():
            print(f"  {k:<18} {s['pass']:>3}/{s['total']:<3} {'PASS' if s['pass'] == s['total'] else 'FAIL'}")
            for r in g[k]:
                if not r["ok"]:
                    print("     ✗", json.dumps(r, ensure_ascii=False, default=str)[:300])
    return ok, g, summary, measured, live


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", choices=["finance", "ecommerce"], default="finance")
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--negative-control", action="store_true")
    ap.add_argument("--only", help="comma separated CQ ids (measure mode)")
    a = ap.parse_args()
    configure_domain(a.domain)
    doc = yaml.safe_load(open(CQ_FILE, encoding="utf-8"))


    if a.measure:
        if a.only:
            keep = set(a.only.split(","))
            doc["cqs"] = [c for c in doc["cqs"] if c["id"] in keep]
        _, measured = gate_queries(doc, measure=True)
        for k, v in measured.items():
            print(f"== {k}  ({len(v['rows'])} rows)")
            for r in v["rows"][:12]:
                print("  ", json.dumps(r, ensure_ascii=False, default=str))
        return 0

    print("[verify_cq] baseline")
    ok, gates, summary, measured, live = run_all(doc)

    nc = None
    if a.negative_control:
        print("[verify_cq] negative controls (each must FAIL its gate)")
        nc = {}
        # NC1: paraphrased (non-verbatim) quote
        d1 = copy.deepcopy(doc)
        d1["cqs"][0]["evidence"][0]["quote"] = "정상분류 자산은 업종 불문 100분의 0.9 이상 적립한다"
        nc["NC1_fake_quote→CQ-G1"] = not all(r["ok"] for r in gate_quotes(d1, d1["sources"]))
        # NC2: fabricated column
        d2 = copy.deepcopy(doc)
        d2["cqs"][0]["data_fields"][0]["columns"].append("min_prov_rate_pct")
        nc["NC2_fake_column→CQ-G2"] = not all(r["ok"] for r in gate_columns(d2, live[0], live[1]))
        # NC3: wrong expected value (0.85% 오답 기준 과소적립 0건)
        d3 = copy.deepcopy(doc)
        d3["cqs"] = [copy.deepcopy(doc["cqs"][0])]
        d3["cqs"][0]["answer_queries"][0]["expect"] = {"exact_rows": 0}
        r3, _ = gate_queries(d3)
        nc["NC3_wrong_expect→CQ-G3"] = not all(r["ok"] for r in r3)
        # NC4: stale pre-ADR-0005 graph label (:DecisionCriteria / [:HAS_EXCEPTION])
        d4 = copy.deepcopy(doc)
        d4["cqs"][0]["graph_path"] = "(:DecisionCriteria{id:'art_029'})-[:HAS_EXCEPTION]->(:ExceptionRule)"
        nc["NC4_stale_graph_label→CQ-G8"] = not all(r["ok"] for r in gate_graph_labels(d4))
        for k, v in nc.items():
            print(f"  {k:<28} {'FAILED as required' if v else 'DID NOT FAIL (gate broken)'}")
        ok = ok and all(nc.values())

    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "ontology/cq/competency_questions.yaml",
        "stores": {"bigquery": f"{PROJECT}.{DATASET} (ont_* = Spanner federated, Data Boost)",
                   "spanner": f"{SPANNER_INSTANCE}/{SPANNER_DB}"},
        "summary": summary, "negative_controls": nc, "result": "PASS" if ok else "FAIL",
        "gates": gates, "measured": measured,
        "spec": doc,  # viewer(docs/cq_studio.js)가 이 파일 하나만 읽도록 원본 YAML 동봉
    }
    json.dump(report, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1,
              default=str)
    print(f"[verify_cq] RESULT: {'PASS' if ok else 'FAIL'} → {os.path.relpath(REPORT, ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
