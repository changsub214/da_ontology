#!/usr/bin/env python3
"""verify_eval.py — RAG vs GraphRAG 평가 질문 게이트 (ontology/eval_question/eval_questions.yaml)

평가 질문 세트가 "GraphRAG 가 이기도록 짠 시험"이 아님을 **실행 전에** 실패 가능한 방식으로 측정한다.
정답 근거 자체는 CQ 와 동일한 방식(원본 PDF verbatim + 라이브 SQL)으로 검증한다.

Gates
  EQ-G1 quote        : evidence.quote 가 선언된 PDF·쪽 원문에 그대로 존재 (verify_cq.quote_found 재사용)
  EQ-G2 queries      : answer_queries 가 라이브(BQ + ont_* 연합 뷰)에서 실행되고 expect 를 만족
  EQ-G3 allocation   : 카테고리 배분 == meta.allocation (8/6/6), category ↔ expected_winner 일관,
                       rag_favored 는 graph_risk(그래프가 질 수 있는 이유) 필수
  EQ-G4 holdout      : CQ 질문과 문장 중복 없음 (정규화 동일 문장 0, 문자 bigram Jaccard < 0.5),
                       sibling_cq 는 실재하는 CQ id
  EQ-G5 grading      : 채점 정규식이 컴파일되고, gold_answer 에 must_include 전부 매치 ·
                       must_not_include 0 매치 (채점기 자기일관성), cite.doc ⊆ evidence.doc
  EQ-G6 structure    : 20문항 · id 중복 없음 · 모든 문항 evidence ≥ 1

Usage
  python tools/verify_eval.py                     # → ontology/eval_question/eval_report.json
  python tools/verify_eval.py --negative-control  # 고의 결함 4종 주입 → 각각 FAIL 나는지 확인
"""
from __future__ import annotations

import argparse, copy, datetime as dt, json, os, re, sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_cq as vc  # noqa: E402

ROOT = vc.ROOT
EQ_FILE = os.path.join(ROOT, "finance", "ontology", "eval_question", "eval_questions.yaml")
REPORT = os.path.join(ROOT, "finance", "ontology", "eval_question", "eval_report.json")

WINNER_OF = {"graph_favored": "graphrag", "rag_favored": "rag", "parity": "tie"}
JACCARD_MAX = 0.5


def bigrams(s: str) -> set[str]:
    s = vc.norm(s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def jaccard(a: str, b: str) -> float:
    x, y = bigrams(a), bigrams(b)
    return len(x & y) / max(1, len(x | y))


def gate_quotes(doc):
    res = []
    for q in doc["questions"]:
        for ev in q["evidence"]:
            fn = doc["sources"][ev["doc"]]["file"]
            ok, hits = vc.quote_found(fn, ev["page"], ev["quote"])
            res.append({"eq": q["id"], "doc": ev["doc"], "page": ev["page"], "ok": ok,
                        "found_on_pages": hits, "quote": ev["quote"][:60]})
    return res


def gate_queries(doc):
    res, measured = [], {}
    for q in doc["questions"]:
        for i, aq in enumerate(q.get("answer_queries", [])):
            key = f"{q['id']}#{i + 1}"
            try:
                cols, rows = vc.run_sql(aq["sql"])
            except Exception as e:  # noqa: BLE001
                res.append({"eq": key, "ok": False, "errors": [f"SQL error: {e}"[:400]]})
                continue
            measured[key] = {"columns": cols, "rows": rows}
            errs = vc.check_expect(aq.get("expect", {}), cols, rows)
            res.append({"eq": key, "ok": not errs, "errors": errs, "row_count": len(rows)})
    return res, measured


def gate_allocation(doc):
    want = doc["meta"]["allocation"]
    got: dict[str, int] = {}
    errs = []
    for q in doc["questions"]:
        got[q["category"]] = got.get(q["category"], 0) + 1
        if WINNER_OF.get(q["category"]) != q.get("expected_winner"):
            errs.append(f"{q['id']}: category {q['category']} vs expected_winner {q.get('expected_winner')}")
        if q["category"] == "rag_favored" and not q.get("graph_risk"):
            errs.append(f"{q['id']}: rag_favored without graph_risk")
    if got != want:
        errs.append(f"allocation {got} != {want}")
    return [{"ok": not errs, "errors": errs, "allocation": got}]


def gate_holdout(doc, cq_doc):
    cqs = {c["id"]: c["question"] for c in cq_doc["cqs"]}
    res = []
    for q in doc["questions"]:
        errs = []
        best_id, best = None, 0.0
        for cid, ctext in cqs.items():
            if vc.norm(ctext) == vc.norm(q["question"]):
                errs.append(f"identical to {cid}")
            j = jaccard(ctext, q["question"])
            if j > best:
                best_id, best = cid, j
        if best >= JACCARD_MAX:
            errs.append(f"too similar to {best_id} (jaccard {best:.2f})")
        sib = q.get("sibling_cq")
        if sib is not None and sib not in cqs:
            errs.append(f"sibling_cq {sib} not found")
        res.append({"eq": q["id"], "ok": not errs, "errors": errs,
                    "max_jaccard": round(best, 3), "nearest_cq": best_id})
    return res


def gate_grading(doc):
    res = []
    for q in doc["questions"]:
        g, gold, errs = q["grading"], q["gold_answer"], []
        for pat in g.get("must_include", []):
            try:
                if not re.search(pat, gold):
                    errs.append(f"must_include not in gold: {pat}")
            except re.error as e:
                errs.append(f"bad regex {pat}: {e}")
        for pat in g.get("must_not_include", []):
            try:
                if re.search(pat, gold):
                    errs.append(f"must_not_include hits gold: {pat}")
            except re.error as e:
                errs.append(f"bad regex {pat}: {e}")
        ev_docs = {ev["doc"] for ev in q["evidence"]}
        for c in g.get("cite", []):
            if c["doc"] not in ev_docs:
                errs.append(f"cite doc {c['doc']} not in evidence docs {sorted(ev_docs)}")
        if not g.get("must_include"):
            errs.append("empty must_include")
        res.append({"eq": q["id"], "ok": not errs, "errors": errs})
    return res


def gate_structure(doc):
    ids = [q["id"] for q in doc["questions"]]
    errs = []
    if len(ids) != 20:
        errs.append(f"count {len(ids)} != 20")
    if len(ids) != len(set(ids)):
        errs.append("duplicate ids")
    errs += [f"{q['id']}: no evidence" for q in doc["questions"] if not q.get("evidence")]
    return [{"ok": not errs, "errors": errs}]


def run_all(doc, cq_doc, *, live_queries=True, verbose=True):
    g = {"EQ-G1_quote": gate_quotes(doc)}
    measured = {}
    if live_queries:
        g["EQ-G2_queries"], measured = gate_queries(doc)
    g["EQ-G3_allocation"] = gate_allocation(doc)
    g["EQ-G4_holdout"] = gate_holdout(doc, cq_doc)
    g["EQ-G5_grading"] = gate_grading(doc)
    g["EQ-G6_structure"] = gate_structure(doc)
    summary = {k: {"pass": sum(1 for r in v if r["ok"]), "total": len(v)} for k, v in g.items()}
    ok = all(s["pass"] == s["total"] for s in summary.values())
    if verbose:
        for k, s in summary.items():
            print(f"  {k:<18} {s['pass']:>3}/{s['total']:<3} {'PASS' if s['pass'] == s['total'] else 'FAIL'}")
            for r in g[k]:
                if not r["ok"]:
                    print("     ✗", json.dumps(r, ensure_ascii=False, default=str)[:300])
    return ok, g, summary, measured


def main():
    global EQ_FILE, REPORT
    ap = argparse.ArgumentParser()
    ap.add_argument("--domain", choices=["finance", "ecommerce"], default="finance")
    ap.add_argument("--negative-control", action="store_true")
    ap.add_argument("--offline", action="store_true", help="skip live SQL gate (EQ-G2)")
    a = ap.parse_args()
    vc.configure_domain(a.domain)
    if a.domain == "ecommerce":
        EQ_FILE = os.path.join(ROOT, "ecommerce", "ontology", "eval_question", "eval_questions.yaml")
        REPORT = os.path.join(ROOT, "ecommerce", "ontology", "eval_question", "eval_report.json")
    else:
        EQ_FILE = os.path.join(ROOT, "finance", "ontology", "eval_question", "eval_questions.yaml")
        REPORT = os.path.join(ROOT, "finance", "ontology", "eval_question", "eval_report.json")
    doc = yaml.safe_load(open(EQ_FILE, encoding="utf-8"))
    cq_doc = yaml.safe_load(open(vc.CQ_FILE, encoding="utf-8"))


    print("[verify_eval] baseline")
    ok, gates, summary, measured = run_all(doc, cq_doc, live_queries=not a.offline)

    nc = None
    if a.negative_control:
        print("[verify_eval] negative controls (each must FAIL its gate)")
        nc = {}
        idx = {q["id"]: i for i, q in enumerate(doc["questions"])}
        # NC1: 비원문 인용
        d = copy.deepcopy(doc)
        d["questions"][idx["EQ15"]]["evidence"][0]["quote"] = "요주의는 2개월 이상 4개월 미만 연체"
        nc["NC1_fake_quote→EQ-G1"] = not all(r["ok"] for r in gate_quotes(d))
        # NC2: 배분 조작 (RAG 우세 문항을 graph_favored 로 재분류)
        d = copy.deepcopy(doc)
        d["questions"][idx["EQ09"]]["category"] = "graph_favored"
        d["questions"][idx["EQ09"]]["expected_winner"] = "graphrag"
        nc["NC2_rigged_allocation→EQ-G3"] = not all(r["ok"] for r in gate_allocation(d))
        # NC3: 홀드아웃 위반 (CQ 문장 그대로 복사)
        d = copy.deepcopy(doc)
        d["questions"][0]["question"] = cq_doc["cqs"][0]["question"]
        nc["NC3_holdout_leak→EQ-G4"] = not all(r["ok"] for r in gate_holdout(d, cq_doc))
        # NC4: 오답 gold (0.85% 로 계산한 금액)
        d = copy.deepcopy(doc)
        d["questions"][idx["EQ01"]]["gold_answer"] = "1억 2,750만 원 (150억 × 0.85%)"
        nc["NC4_wrong_gold→EQ-G5"] = not all(r["ok"] for r in gate_grading(d))
        for k, v in nc.items():
            print(f"  {k:<30} {'FAILED as required' if v else 'DID NOT FAIL (gate broken)'}")
        ok = ok and all(nc.values())

    report = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": "ontology/eval_question/eval_questions.yaml",
        "summary": summary, "negative_controls": nc, "result": "PASS" if ok else "FAIL",
        "gates": gates, "measured": measured,
        "spec": doc,  # viewer(docs/cq_studio.js)가 이 파일 하나만 읽도록 원본 YAML 동봉
    }
    if not a.offline:
        json.dump(report, open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1,
                  default=str)
    print(f"[verify_eval] RESULT: {'PASS' if ok else 'FAIL'} → {os.path.relpath(REPORT, ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
