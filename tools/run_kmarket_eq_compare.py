#!/usr/bin/env python3
"""K-Market (ecommerce-ontology) EQ 20 comparison: RAG arm vs Graph arm, judged by an ADK Gemini judge.

  collect : ask all 20 EQs to both deployed Agent Runtime engines (`kmarket-graph-agent` & `kmarket-rag-agent`)
            -> ecommerce/ontology/eval_question/compare_run.json
  judge   : ADK LlmAgent judge (output_schema) per answer, against gold_answer + evidence
            -> okf_veri_web/data/ecommerce/eq_compare.json
"""
from __future__ import annotations

import asyncio
import concurrent.futures as cf
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.request
from typing import Literal

import yaml

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ.setdefault("GOOGLE_API_USE_MTLS_ENDPOINT", "never")
os.environ.setdefault("CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE", "false")

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from agent_remote_client import _access_token, execute_kmarket_agent_chat, kmarket_agent_resource  # noqa: E402
from rag_remote_client import kmarket_rag_agent_resource  # noqa: E402

EQ_PATH = ROOT / "ecommerce/ontology/eval_question/eval_questions.yaml"
RUN_PATH = ROOT / "ecommerce/ontology/eval_question/compare_run.json"
OUT_PATH = ROOT / "okf_veri_web/data/ecommerce/eq_compare.json"

RAG_CORPUS = "projects/567090080191/locations/us-central1/ragCorpora/178446339141533696"
USER_ID = "eq_compare_kmarket"
JUDGE_MODEL = os.environ.get("STARLIGHT_JUDGE_MODEL", "gemini-3.8-flash")
WORKERS = int(os.environ.get("EQ_COMPARE_WORKERS", "5"))
MASK = ("finance-ontology-changseop", "567090080191")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mask(s: str) -> str:
    if not s:
        return ""
    return (
        s.replace(f"{MASK[0]}.", "")
        .replace(MASK[0], "kmarket-gcp-project")
        .replace(MASK[1], "000000000000")
        .replace("gs://kmarket_okf/", "gs://okf/")
    )


def _mask_obj(v):
    if isinstance(v, str):
        return _mask(v)
    if isinstance(v, list):
        return [_mask_obj(x) for x in v]
    if isinstance(v, dict):
        return {k: _mask_obj(val) for k, val in v.items()}
    return v


def ask_graphrag(q: str) -> dict:
    t0 = time.time()
    try:
        res = execute_kmarket_agent_chat({"question": q})
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:500], "elapsed_s": round(time.time() - t0, 1)}
    tr = res.get("adk_trace") or {}
    keep = (
        "mode",
        "reason",
        "tool_calls_used",
        "blocked",
        "dropped_provision_slots",
        "used_canned_cq_assets",
        "touched_kc_entry_ids",
        "gql_repaired",
        "gql_row_count",
        "governance_gate_blocks",
        "gql_status",
        "gql_repair_rounds",
        "gql_validations",
        "gql_executions",
        "gql_stop_reason",
    )
    provs = (res.get("artifact_drawer") or {}).get("provisions") or []
    fetched_keys = [
        p.get("provision_slot_id") or p.get("kc_entry_id")
        for p in provs
        if p.get("provision_slot_id") or p.get("kc_entry_id")
    ]
    return {
        "question": q,
        "collected_at": _now(),
        "answer": _mask(res.get("answer_markdown") or ""),
        "mode": tr.get("mode"),
        "tool_calls": tr.get("tool_calls_used"),
        "trace": {
            **{k: tr.get(k) for k in keep if k in tr},
            "internal_key": res.get("internal_key"),
            "blocked_result": bool(res.get("blocked")),
            "refused_result": bool(res.get("refused")),
            "fetched": fetched_keys,
        },
        "gql_accordion": _mask_obj(res.get("gql_accordion") or {}),
        "artifact_drawer": _mask_obj(res.get("artifact_drawer") or {}),
        "elapsed_s": round(time.time() - t0, 1),
    }


def ask_rag(q: str) -> dict:
    t0 = time.time()
    rag_engine = kmarket_rag_agent_resource()
    body = json.dumps({"class_method": "stream_query", "input": {"user_id": USER_ID, "message": q}}, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f"https://us-central1-aiplatform.googleapis.com/v1/{rag_engine}:streamQuery",
        data=body,
        headers={"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"},
        method="POST",
    )
    out = {
        "question": q,
        "collected_at": _now(),
        "answer": "",
        "rag_calls": 0,
        "sql_calls": 0,
        "rag_query": "",
        "rag_chunks": [],
        "sql": "",
        "sql_status": "",
    }
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            for raw in r:
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                ev = json.loads(line)
                if ev.get("error_code"):
                    raise RuntimeError(f"{ev.get('error_code')}: {ev.get('error_message')}")
                for p in (ev.get("content") or {}).get("parts") or []:
                    if not isinstance(p, dict):
                        continue
                    fc, fr = p.get("function_call"), p.get("function_response")
                    if fc and fc.get("name") == "vertex_rag_search":
                        out["rag_calls"] += 1
                        out["rag_query"] = _mask((fc.get("args") or {}).get("query", ""))
                    elif fc and fc.get("name") == "execute_sql":
                        out["sql_calls"] += 1
                        out["sql"] = _mask((fc.get("args") or {}).get("query", ""))
                    elif fr and fr.get("name") == "vertex_rag_search":
                        out["rag_chunks"] = [
                            {
                                "doc_id": c.get("doc_id"),
                                "source": c.get("source"),
                                "score": c.get("score"),
                                "text": _mask((c.get("text") or "")[:600]),
                            }
                            for c in ((fr.get("response") or {}).get("contexts") or [])[:3]
                        ]
                    elif fr and fr.get("name") == "execute_sql":
                        out["sql_status"] = _mask(str((fr.get("response") or {}).get("status", "")))
                    if ev.get("author") == "answer_step" and p.get("text"):
                        out["answer"] += _mask(str(p["text"]))
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"[:500]
    out["elapsed_s"] = round(time.time() - t0, 1)
    return out


def _eq_doc() -> dict:
    return yaml.safe_load(EQ_PATH.read_text(encoding="utf-8"))


def _ask_with_retry(arm: str, text: str, attempts: int = 3) -> dict:
    fn = ask_graphrag if arm == "graphrag" else ask_rag
    r: dict = {}
    for i in range(attempts):
        r = fn(text)
        if not r.get("error") and r.get("answer"):
            break
        time.sleep(4 * (i + 1))
    r["attempts"] = i + 1
    return r


def cmd_collect(arms: list[str], ids: list[str]) -> int:
    eq_doc = _eq_doc()
    all_ids = [q["id"] for q in eq_doc["questions"]]
    unknown = sorted(set(ids) - set(all_ids))
    if unknown:
        print(f"unknown ids: {unknown}")
        return 2
    eqs = [q for q in eq_doc["questions"] if not ids or q["id"] in ids]
    partial = bool(ids) or set(arms) != {"graphrag", "rag"}
    started = _now()
    jobs = [(q["id"], arm, q["question"]) for q in eqs for arm in arms]

    if partial and RUN_PATH.exists():
        doc = json.loads(RUN_PATH.read_text(encoding="utf-8"))
    else:
        doc = {"meta": {}, "results": {}}
    res = doc["results"]
    for qid in all_ids:
        res.setdefault(qid, {})

    def run(job):
        qid, arm, text = job
        return qid, arm, _ask_with_retry(arm, text)

    with cf.ThreadPoolExecutor(WORKERS * 2) as ex:
        for qid, arm, r in ex.map(run, jobs):
            res[qid][arm] = r
            extra = (
                f"mode {r.get('mode')} calls {r.get('tool_calls')}"
                if arm == "graphrag"
                else f"rag {r.get('rag_calls')} chunks {len(r.get('rag_chunks') or [])} sql {r.get('sql_calls')}"
            )
            print(
                f"{qid} {arm:8s} {r.get('elapsed_s'):6}s try {r.get('attempts')} {extra} {'ERR ' + r['error'] if r.get('error') else ''}",
                flush=True,
            )

    run_meta = {
        "started_at": started,
        "finished_at": _now(),
        "arms": list(arms),
        "ids": [q["id"] for q in eqs] if ids else "all",
        "eq_version": eq_doc["meta"]["version"],
        "graphrag_engine": kmarket_agent_resource(),
        "rag_engine": kmarket_rag_agent_resource(),
    }
    meta = doc.get("meta") or {}
    meta.update({
        "runs_per_question": 1,
        "graphrag_engine": kmarket_agent_resource(),
        "rag_engine": kmarket_rag_agent_resource(),
        "rag_corpus": RAG_CORPUS,
        "model": "gemini-3.8-flash (global)",
        "eq_source": str(EQ_PATH.relative_to(ROOT)),
        "eq_version": eq_doc["meta"]["version"],
    })
    if partial:
        meta.setdefault("collections", []).append(run_meta)
    else:
        meta.update({"started_at": started, "finished_at": run_meta["finished_at"], "collections": [run_meta]})
    doc["meta"] = meta
    RUN_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    errs = sum(1 for qid, arm, _ in jobs if res[qid][arm].get("error") or not res[qid][arm].get("answer"))
    print(f"wrote {RUN_PATH.relative_to(ROOT)} · {'partial' if partial else 'full'} · answers {len(jobs) - errs}/{len(jobs)} · errors {errs}")
    return 0 if errs == 0 else 1


JUDGE_INSTRUCTION = """당신은 한국 이커머스·유통(MD 마진·CRM 추천·대규모유통업법 판촉비 정산·전자상거래법 반품심사·물류 SLA) 분야의 엄격한 채점관입니다. 한 질문에 대한 에이전트 답변 하나가 **맞았는지 틀렸는지만** 판정합니다.

판정 기준 (정답 = 아래 '정답'과 '근거'):
- correct: 답변의 핵심 결론(금액·비율·건수·판정/허용 여부·해당 조문/예외승인 ID/사유)이 정답과 모두 일치한다. 표현·서술 순서·부가 설명 차이는 문제 삼지 않는다.
- incorrect: 핵심 수치·비율·건수·결론이 정답과 다르다 / 정답이 요구한 핵심 예외승인 ID(예: EXC-KM-2026-07, EXC-KM-2026-03 등)나 조문·본부별 분기 수치를 누락하거나 잘못 적용했다 / 정답이 함정으로 명시한 값·규칙을 썼다 / 답을 내지 못했다(거부·"확인되지 않음"·SQL 오류) / 질문과 다른 것을 답했다.
- 핵심 결론은 맞지만 정답이 요구한 필수 항목 일부가 빠졌다면, 그 누락이 결론을 바꾸지 않을 때만 correct 로 하고 missing 에 적는다.

wrong_spans: incorrect 일 때 답변에서 **틀린 부분을 답변 원문 그대로(한 글자도 바꾸지 말고) 복사**해 quote 에 넣고, why 에 정답과 무엇이 다른지(또는 어떤 문서/테이블 간 관계를 놓쳤는지) 한 문장으로 쓴다. 최대 4개, 각 quote 는 80자 이내의 연속된 원문 조각. 답을 못 낸 경우 그 문장을 quote 로 쓴다. correct 이면 빈 목록.
reason: 판정 이유를 한국어 한두 문장으로 구체적으로 작성한다.
정답 자체의 옳고 그름은 따지지 말고 주어진 정답 기준으로만 판정한다."""


def _judge_agent():
    from google.adk.agents import LlmAgent
    from google.genai import types
    from pydantic import BaseModel, Field

    class WrongSpan(BaseModel):
        quote: str = Field(description="답변 원문에서 그대로 복사한 틀린 부분 (80자 이내)")
        why: str = Field(description="정답과 무엇이 다른지 한 문장")

    class Verdict(BaseModel):
        verdict: Literal["correct", "incorrect"]
        reason: str
        wrong_spans: list[WrongSpan] = Field(default_factory=list)
        missing: list[str] = Field(default_factory=list, description="정답이 요구했지만 답변에 없는 항목")

    return LlmAgent(
        name="eq_judge_kmarket",
        model=JUDGE_MODEL,
        instruction=JUDGE_INSTRUCTION,
        output_schema=Verdict,
        output_key="verdict",
        generate_content_config=types.GenerateContentConfig(temperature=0, seed=20260927),
    )


_IGNORED = set("*`\\$")


def _normalize(s: str) -> tuple[str, list[int]]:
    chars, idx = [], []
    for i, ch in enumerate(s):
        if ch in _IGNORED:
            continue
        if ch.isspace():
            if chars and chars[-1] == " ":
                continue
            ch = " "
        chars.append(ch)
        idx.append(i)
    return "".join(chars), idx


def _locate(quote: str, answer: str) -> tuple[int, int] | None:
    if not quote:
        return None
    pos = answer.find(quote)
    if pos >= 0:
        return pos, pos + len(quote)
    na, amap = _normalize(answer)
    nq, _ = _normalize(quote)
    nq = nq.strip()
    pos = na.find(nq) if nq else -1
    if pos < 0:
        return None
    return amap[pos], amap[pos + len(nq) - 1] + 1


def _judge_prompt(q: dict, answer: str) -> str:
    ev = "\n".join(f"- 문서 {e.get('doc')} p.{e.get('page')}: {e.get('quote')}" for e in q.get("evidence") or [])
    must_inc = ", ".join(str(x) for x in ((q.get("grading") or {}).get("must_include") or []))
    return (
        f"## 질문\n{q['question']}\n\n## 정답\n{q.get('gold_answer')}\n\n"
        f"## 필수 포함 요소 (참고)\n{must_inc}\n\n"
        f"## 근거\n{ev or '(없음)'}\n\n"
        f"## 에이전트 답변\n{answer or '(빈 답변)'}"
    )


async def _judge_all(items: list[tuple[str, str, dict, str]]) -> dict:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", MASK[0])
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(agent=_judge_agent(), app_name="eq_judge_kmarket")
    sem = asyncio.Semaphore(WORKERS)
    out: dict = {}

    async def one(qid, arm, q, answer):
        async with sem:
            for attempt in range(3):
                try:
                    s = await runner.session_service.create_session(app_name="eq_judge_kmarket", user_id="judge")
                    async for _ in runner.run_async(
                        user_id="judge",
                        session_id=s.id,
                        new_message=types.Content(role="user", parts=[types.Part(text=_judge_prompt(q, answer))]),
                    ):
                        pass
                    s = await runner.session_service.get_session(
                        app_name="eq_judge_kmarket", user_id="judge", session_id=s.id
                    )
                    v = s.state.get("verdict")
                    if isinstance(v, str):
                        v = json.loads(v)
                    break
                except Exception as e:  # noqa: BLE001
                    v = {"verdict": "error", "reason": f"{type(e).__name__}: {e}"[:300], "wrong_spans": [], "missing": []}
                    await asyncio.sleep(3 * (attempt + 1))
            spans = []
            for sp in v.get("wrong_spans") or []:
                loc = _locate(sp.get("quote", ""), answer)
                spans.append({
                    **sp,
                    "found": loc is not None,
                    "start": loc[0] if loc else None,
                    "end": loc[1] if loc else None,
                })
            v["wrong_spans"] = spans
            out.setdefault(qid, {})[arm] = v
            print(
                f"{qid} {arm:8s} {v.get('verdict'):9s} spans {len(spans)} (found {sum(s['found'] for s in spans)}) | {v.get('reason', '')[:80]}",
                flush=True,
            )

    await asyncio.gather(*(one(*it) for it in items))
    return out


ARMS = ("graphrag", "rag")
ROW_KEYS = ("id", "category", "expected_winner", "question", "gold_answer", "evidence", "rationale")


def _row_head(qid: str, q: dict) -> dict:
    return {
        "id": qid,
        "category": q.get("category"),
        "expected_winner": q.get("expected_winner"),
        "question": q["question"],
        "gold_answer": q.get("gold_answer"),
        "evidence": q.get("evidence") or [],
        "rationale": q.get("rationale"),
    }


def cmd_judge(ids: list[str] | None = None, arms: list[str] | None = None) -> int:
    eq_doc = _eq_doc()
    eqs = {q["id"]: q for q in eq_doc["questions"]}
    run = json.loads(RUN_PATH.read_text(encoding="utf-8"))
    sel_ids = list(ids) if ids else list(eqs)
    sel_arms = tuple(a for a in ARMS if a in (arms or ARMS))
    selected = {(qid, arm) for qid in sel_ids for arm in sel_arms}

    items = [
        (qid, arm, eqs[qid], (run["results"][qid].get(arm) or {}).get("answer", ""))
        for qid in eqs
        for arm in ARMS
        if (qid, arm) in selected
    ]
    started = _now()
    verdicts = asyncio.run(_judge_all(items))

    questions = []
    for qid, q in eqs.items():
        row = _row_head(qid, q)
        for arm in ARMS:
            a = run["results"][qid].get(arm) or {}
            row[arm] = {**{k: v for k, v in a.items()}, "judge": verdicts.get(qid, {}).get(arm)}
        questions.append(row)

    counts = {
        arm: sum(1 for r in questions if (r[arm]["judge"] or {}).get("verdict") == "correct")
        for arm in ARMS
    }
    meta = {k: (_mask(v) if isinstance(v, str) else v) for k, v in run["meta"].items()}
    meta["collections"] = [
        {k: (_mask(v) if isinstance(v, str) else v) for k, v in c.items()}
        for c in run["meta"].get("collections") or []
    ]
    doc = {
        "meta": {
            **meta,
            "eq_version": eq_doc["meta"]["version"],
            "judged_at": started,
            "judge": {
                "framework": "ADK LlmAgent (output_schema)",
                "model": f"{JUDGE_MODEL} (global)",
                "temperature": 0,
                "instruction": JUDGE_INSTRUCTION,
            },
            "rules": {"out_of_domain": None},
            "note": "라이브 시연용 정적 비교. 점수 없음 — 맞음/틀림과 틀린 부분만. 정답 기준은 eval_questions.yaml gold_answer.",
        },
        "summary": {
            "total": len(questions),
            "correct": counts,
            "rule_applied": {"out_of_domain": []},
            "question_unchecked": [],
            "errors": sum(
                1
                for r in questions
                for arm in ARMS
                if (r[arm]["judge"] or {}).get("verdict") not in ("correct", "incorrect")
            ),
        },
        "questions": questions,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    leaks = sum(OUT_PATH.read_text(encoding="utf-8").count(m) for m in MASK)
    n = len(questions)
    print(
        f"wrote {OUT_PATH.relative_to(ROOT)} · eq v{eq_doc['meta']['version']} · "
        f"correct GraphRAG {counts['graphrag']}/{n} · RAG {counts['rag']}/{n} · "
        f"judge errors {doc['summary']['errors']} · project-id leaks {leaks}"
    )
    return 0 if doc["summary"]["errors"] == 0 and leaks == 0 else 1


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect", help="ask EQs to the deployed K-Market engines")
    c.add_argument("--arms", default="graphrag,rag", help="comma list: graphrag,rag")
    c.add_argument("--ids", default="", help="comma list of EQ ids (default: all)")
    j = sub.add_parser("judge", help="ADK judge over compare_run.json -> okf_veri_web/data/ecommerce/eq_compare.json")
    j.add_argument("--arms", default="graphrag,rag", help="comma list: graphrag,rag")
    j.add_argument("--ids", default="", help="comma list of EQ ids")
    a = ap.parse_args()
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    ids = [x.strip() for x in a.ids.split(",") if x.strip()]
    if a.cmd == "collect":
        sys.exit(cmd_collect(arms, ids))
    sys.exit(cmd_judge(ids, arms))
