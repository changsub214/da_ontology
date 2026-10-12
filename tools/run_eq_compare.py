"""EQ 20 comparison: RAG arm vs GraphRAG arm, one run each, judged right/wrong by a Gemini judge (ADK agent).

  collect : ask all EQs to both deployed Agent Runtime engines -> ontology/eval_question/compare_run.json
  judge   : ADK LlmAgent judge (output_schema) per answer, against gold_answer + evidence
            -> okf_veri_web/data/eq_compare.json (static; Module 06 reads only this, no live calls)

Run with the GraphRAG venv (ADK + PyYAML):
  uv run --frozen --project agents/starlight-graphrag python tools/run_eq_compare.py collect
  uv run --frozen --project agents/starlight-graphrag python tools/run_eq_compare.py judge

No numeric score (user decision 2026-09-27): verdict is correct / incorrect, plus the wrong spans quoted verbatim
from the answer so the UI can mark them. Design: agents/design/rag_agent_v0.yaml eval_run.
"""
from __future__ import annotations

import asyncio
import concurrent.futures as cf
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.request
from typing import Literal

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from agent_remote_client import agent_resource, execute_agent_chat  # noqa: E402

EQ_PATH = ROOT / "finance/ontology/eval_question/eval_questions.yaml"
RUN_PATH = ROOT / "finance/ontology/eval_question/compare_run.json"
OUT_PATH = ROOT / "okf_veri_web/data/eq_compare.json"

RAG_ENGINE = os.environ.get(
    "STARLIGHT_RAG_AGENT_RESOURCE", "projects/567090080191/locations/us-central1/reasoningEngines/817539122053775360"
)
RAG_CORPUS = "projects/567090080191/locations/us-central1/ragCorpora/6976207764192231424"
USER_ID = "eq_compare"
JUDGE_MODEL = os.environ.get("STARLIGHT_JUDGE_MODEL", "gemini-3.8-flash")
WORKERS = int(os.environ.get("EQ_COMPARE_WORKERS", "4"))
MASK = ("finance-ontology-changseop", "567090080191")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _token() -> str:
    env = dict(os.environ, CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE="false")
    return subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True, env=env).stdout.strip()


def _mask(s: str) -> str:
    return s.replace(f"{MASK[0]}.", "").replace(MASK[0], "starlight-gcp-project").replace(MASK[1], "000000000000")


def _mask_obj(v):
    if isinstance(v, str):
        return _mask(v)
    if isinstance(v, list):
        return [_mask_obj(x) for x in v]
    if isinstance(v, dict):
        return {k: _mask_obj(val) for k, val in v.items()}
    return v


# ---------------------------------------------------------------------------
# collect
# ---------------------------------------------------------------------------
def ask_graphrag(q: str) -> dict:
    t0 = time.time()
    try:
        res = execute_agent_chat({"question": q})
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"[:500], "elapsed_s": round(time.time() - t0, 1)}
    tr = res.get("adk_trace") or {}
    keep = ("mode", "reason", "tool_calls_used", "blocked", "dropped_provision_slots", "used_canned_cq_assets",
            "touched_kc_entry_ids", "gql_repaired", "gql_row_count", "governance_gate_blocks",
            # Step 1 loop (ADR 0016): validate → repair ≤ cap → execute once; refused when nothing passes
            "gql_status", "gql_repair_rounds", "gql_validations", "gql_executions", "gql_stop_reason")
    return {
        "question": q,
        "collected_at": _now(),
        "answer": res.get("answer_markdown") or "",
        "mode": tr.get("mode"),
        "tool_calls": tr.get("tool_calls_used"),
        "trace": {
            **{k: tr.get(k) for k in keep if k in tr},
            "internal_key": res.get("internal_key"),
            "blocked_result": bool(res.get("blocked")),
            "refused_result": bool(res.get("refused")),
            "fetched": [e.get("key") for e in (tr.get("evidence_ledger") or []) if e.get("tool") == "fetch_provision"],
        },
        "gql_accordion": _mask_obj(res.get("gql_accordion") or {}),
        "elapsed_s": round(time.time() - t0, 1),
    }


def ask_rag(q: str) -> dict:
    t0 = time.time()
    body = json.dumps({"class_method": "stream_query", "input": {"user_id": USER_ID, "message": q}}, ensure_ascii=False).encode()
    req = urllib.request.Request(
        f"https://us-central1-aiplatform.googleapis.com/v1/{RAG_ENGINE}:streamQuery", data=body,
        headers={"Authorization": f"Bearer {_token()}", "Content-Type": "application/json"}, method="POST")
    out = {"question": q, "collected_at": _now(), "answer": "", "rag_calls": 0, "sql_calls": 0, "rag_query": "",
           "rag_chunks": [], "sql": "", "sql_status": ""}
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
                    fc, fr = p.get("function_call"), p.get("function_response")
                    if fc and fc.get("name") == "vertex_rag_search":
                        out["rag_calls"] += 1
                        out["rag_query"] = (fc.get("args") or {}).get("query", "")
                    elif fc and fc.get("name") == "execute_sql":
                        out["sql_calls"] += 1
                        out["sql"] = _mask((fc.get("args") or {}).get("query", ""))
                    elif fr and fr.get("name") == "vertex_rag_search":
                        out["rag_chunks"] = [
                            {"doc_id": c.get("doc_id"), "source": c.get("source"), "score": c.get("score"), "text": (c.get("text") or "")[:600]}
                            for c in ((fr.get("response") or {}).get("contexts") or [])
                        ]
                    elif fr and fr.get("name") == "execute_sql":
                        out["sql_status"] = str((fr.get("response") or {}).get("status", ""))
                    if ev.get("author") == "answer_step" and p.get("text"):
                        out["answer"] += p["text"]
    except Exception as e:  # noqa: BLE001
        out["error"] = f"{type(e).__name__}: {e}"[:500]
    out["elapsed_s"] = round(time.time() - t0, 1)
    return out


def _eq_doc() -> dict:
    return yaml.safe_load(EQ_PATH.read_text(encoding="utf-8"))


def _ask_with_retry(arm: str, text: str, attempts: int = 3) -> dict:
    """Transient engine/model errors (e.g. Gemini 500 INTERNAL, seen 2026-09-28) are retried; the last try is kept."""
    fn = ask_graphrag if arm == "graphrag" else ask_rag
    r: dict = {}
    for i in range(attempts):
        r = fn(text)
        if not r.get("error") and r.get("answer"):
            break
        time.sleep(5 * (i + 1))
    r["attempts"] = i + 1
    return r


def cmd_collect(arms: list[str], ids: list[str]) -> int:
    """Full run (default) rewrites compare_run.json. With --arms/--ids only those (id, arm) cells are re-asked and
    merged into the existing file; every run is appended to meta.collections so each answer's provenance stays visible."""
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
            extra = f"mode {r.get('mode')} calls {r.get('tool_calls')}" if arm == "graphrag" else f"rag {r.get('rag_calls')} sql {r.get('sql_calls')}"
            print(f"{qid} {arm:8s} {r.get('elapsed_s'):6}s try {r.get('attempts')} {extra} {'ERR ' + r['error'] if r.get('error') else ''}", flush=True)

    run_meta = {
        "started_at": started, "finished_at": _now(), "arms": list(arms), "ids": [q["id"] for q in eqs] if ids else "all",
        "eq_version": eq_doc["meta"]["version"], "graphrag_engine": agent_resource(), "rag_engine": RAG_ENGINE,
    }
    meta = doc.get("meta") or {}
    if partial and "collections" not in meta and meta.get("started_at"):
        # first partial update of a legacy single-run file: keep that run as the first provenance entry
        meta["collections"] = [{"started_at": meta.get("started_at"), "finished_at": meta.get("finished_at"),
                                "arms": ["graphrag", "rag"], "ids": "all", "eq_version": meta.get("eq_version", "1.1.0"),
                                "graphrag_engine": meta.get("graphrag_engine"), "rag_engine": meta.get("rag_engine")}]
    meta.update({
        "runs_per_question": 1, "graphrag_engine": agent_resource(), "rag_engine": RAG_ENGINE, "rag_corpus": RAG_CORPUS,
        "model": "gemini-3.8-flash (global)", "eq_source": str(EQ_PATH.relative_to(ROOT)), "eq_version": eq_doc["meta"]["version"],
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


# ---------------------------------------------------------------------------
# judge (ADK agent)
# ---------------------------------------------------------------------------
JUDGE_INSTRUCTION = """당신은 한국 은행 여신·리스크·준법 분야의 채점관입니다. 한 질문에 대한 에이전트 답변 하나가 **맞았는지 틀렸는지만** 판정합니다.

판정 기준 (정답 = 아래 '정답'과 '근거'):
- correct: 답변의 핵심 결론(금액·비율·건수·판정/허용 여부·해당 조문/사유)이 정답과 일치한다. 표현·서술 순서·부가 설명 차이, 정답에 없는 보충 정보는 문제 삼지 않는다.
- incorrect: 핵심 수치·비율·결론이 정답과 다르다 / 정답이 함정으로 명시한 값·규칙을 썼다 / 답을 내지 못했다(거부·"확인되지 않음") / 질문과 다른 것을 답했다.
- 핵심 결론은 맞지만 정답이 요구한 필수 항목 일부가 빠졌다면, 그 누락이 결론을 바꾸지 않을 때만 correct 로 하고 missing 에 적는다.

wrong_spans: incorrect 일 때 답변에서 **틀린 부분을 답변 원문 그대로(한 글자도 바꾸지 말고) 복사**해 quote 에 넣고, why 에 정답과 무엇이 다른지 한 문장으로 쓴다. 최대 4개, 각 quote 는 80자 이내의 연속된 원문 조각. 답을 못 낸 경우 그 문장을 quote 로 쓴다. correct 이면 빈 목록.
reason: 판정 이유를 한국어 한두 문장으로.
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
        name="eq_judge",
        model=JUDGE_MODEL,
        instruction=JUDGE_INSTRUCTION,
        output_schema=Verdict,
        output_key="verdict",
        generate_content_config=types.GenerateContentConfig(temperature=0, seed=20260927),
    )


_IGNORED = set("*`\\$")


def _normalize(s: str) -> tuple[str, list[int]]:
    """Drop markdown/LaTeX markers, collapse whitespace; keep a map to original indices."""
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
    """Offsets [start, end) of the judge's quote in the original answer, ignoring markdown markers."""
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
    return (
        f"## 질문\n{q['question']}\n\n## 정답\n{q.get('gold_answer')}\n\n## 근거\n{ev or '(없음)'}\n\n"
        f"## 에이전트 답변\n{answer or '(빈 답변)'}"
    )


async def _judge_all(items: list[tuple[str, str, dict, str]]) -> dict:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
    os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", MASK[0])
    from google.adk.runners import InMemoryRunner
    from google.genai import types

    runner = InMemoryRunner(agent=_judge_agent(), app_name="eq_judge")
    sem = asyncio.Semaphore(WORKERS)
    out: dict = {}

    async def one(qid, arm, q, answer):
        async with sem:
            for attempt in range(3):
                try:
                    s = await runner.session_service.create_session(app_name="eq_judge", user_id="judge")
                    async for _ in runner.run_async(user_id="judge", session_id=s.id, new_message=types.Content(
                            role="user", parts=[types.Part(text=_judge_prompt(q, answer))])):
                        pass
                    s = await runner.session_service.get_session(app_name="eq_judge", user_id="judge", session_id=s.id)
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
                spans.append({**sp, "found": loc is not None, "start": loc[0] if loc else None, "end": loc[1] if loc else None})
            v["wrong_spans"] = spans
            out.setdefault(qid, {})[arm] = v
            print(f"{qid} {arm:8s} {v.get('verdict'):9s} spans {len(spans)} (found {sum(s['found'] for s in spans)})", flush=True)

    await asyncio.gather(*(one(*it) for it in items))
    return out


OOD_REASON = {
    "graphrag": "범위 통제 규칙: Graph Agent 가 업무 범위 밖(OUT_OF_DOMAIN)으로 거절 → 정답 (사용자 결정 2026-09-28, ADR 0013)",
    "rag": "범위 통제 규칙: Graph Agent 가 업무 범위 밖으로 거절한 질문에 답함 → 오답 (사용자 결정 2026-09-28, ADR 0013)",
}


def _ood_wrap(arm: str, v: dict) -> dict:
    """protocol.scoring.out_of_domain_rule for one cell; the LLM judge's own verdict is kept as content_judge."""
    if arm == "graphrag":
        return {"verdict": "correct", "rule": "out_of_domain", "reason": OOD_REASON["graphrag"],
                "wrong_spans": [], "missing": [], "content_judge": v}
    return {"verdict": "incorrect", "rule": "out_of_domain", "reason": OOD_REASON["rag"],
            "wrong_spans": v.get("wrong_spans") or [], "missing": v.get("missing") or [], "content_judge": v}


def _is_ood(qid: str, run: dict) -> bool:
    return (run["results"][qid].get("graphrag") or {}).get("mode") == "OUT_OF_DOMAIN"


def _apply_out_of_domain_rule(qid: str, run: dict, verdicts: dict) -> bool:
    """eval_questions.yaml protocol.scoring.out_of_domain_rule. The LLM judge's own verdict is kept as content_judge."""
    if not _is_ood(qid, run):
        return False
    for arm in ("graphrag", "rag"):
        verdicts[qid][arm] = _ood_wrap(arm, verdicts[qid][arm])
    return True


ARMS = ("graphrag", "rag")
ROW_KEYS = ("id", "category", "expected_winner", "question", "gold_answer", "evidence", "rationale")


def _row_head(qid: str, q: dict) -> dict:
    return {
        "id": qid, "category": q.get("category"), "expected_winner": q.get("expected_winner"),
        "question": q["question"], "gold_answer": q.get("gold_answer"),
        "evidence": q.get("evidence") or [], "rationale": q.get("rationale"),
    }


def cmd_judge(ids: list[str] | None = None, arms: list[str] | None = None) -> int:
    """Full run (default) judges all 40 cells. With --ids/--arms only those cells are re-judged; every other cell keeps
    its verdict from the current eq_compare.json byte-for-byte (option C, user decision 2026-09-29), behind gates that
    abort before anything is written."""
    eq_doc = _eq_doc()
    eqs = {q["id"]: q for q in eq_doc["questions"]}
    run = json.loads(RUN_PATH.read_text(encoding="utf-8"))
    unknown = sorted(set(ids or []) - set(eqs))
    if unknown:
        print(f"unknown ids: {unknown}")
        return 2
    sel_ids = list(ids) if ids else list(eqs)
    sel_arms = tuple(a for a in ARMS if a in (arms or ARMS))
    partial = bool(ids) or set(sel_arms) != set(ARMS)
    selected = {(qid, arm) for qid in sel_ids for arm in sel_arms}

    # Gate: an answer must belong to the current question wording (EQ02 was reworded in v1.2.0).
    stale, unchecked = [], []
    for qid, q in eqs.items():
        for arm in ARMS:
            asked = (run["results"][qid].get(arm) or {}).get("question")
            if asked is None:
                unchecked.append(f"{qid}/{arm}")
            elif asked != q["question"]:
                stale.append(f"{qid}/{arm}")
    if stale:
        print(f"ABORT: answers collected for a different question wording: {stale} — re-collect with --ids/--arms")
        return 1

    base, brow = None, {}
    if partial:
        if not OUT_PATH.exists():
            print(f"ABORT: partial judge needs an existing {OUT_PATH.relative_to(ROOT)} to reuse verdicts from")
            return 1
        base = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        brow = {r["id"]: r for r in base.get("questions") or []}
        bj = (base.get("meta") or {}).get("judge") or {}
        if bj.get("instruction") != JUDGE_INSTRUCTION or bj.get("model") != f"{JUDGE_MODEL} (global)":
            print("ABORT: judge model/instruction differ from the base eq_compare.json — reused verdicts would mix judges; run a full judge")
            return 1
        # reused cells: the record in compare_run.json must be exactly the one the base file judged
        drift = [f"{qid}/{arm}" for qid in eqs for arm in ARMS if (qid, arm) not in selected
                 and {k: v for k, v in ((brow.get(qid) or {}).get(arm) or {}).items() if k != "judge"} != (run["results"][qid].get(arm) or {})]
        # every row: question / gold / evidence must be what the base verdicts were judged against
        gold_drift = [qid for qid, q in eqs.items() if {k: (brow.get(qid) or {}).get(k) for k in ROW_KEYS} != _row_head(qid, q)]
        # out-of-domain rule spans both arms of a question: its status must not change under a partial judge
        base_ood = set(((base.get("summary") or {}).get("rule_applied") or {}).get("out_of_domain") or [])
        ood_flip = [qid for qid in sel_ids if _is_ood(qid, run) != (qid in base_ood)]
        if drift or gold_drift or ood_flip:
            print(f"ABORT: partial judge gates — record drift {drift} · question/gold drift {gold_drift} · out-of-domain status changed {ood_flip}")
            return 1

    items = [(qid, arm, eqs[qid], (run["results"][qid].get(arm) or {}).get("answer", ""))
             for qid in eqs for arm in ARMS if (qid, arm) in selected]
    started = _now()
    verdicts = asyncio.run(_judge_all(items))
    if partial:
        for qid in sel_ids:
            if _is_ood(qid, run):
                for arm in sel_arms:
                    verdicts[qid][arm] = _ood_wrap(arm, verdicts[qid][arm])
        for qid in eqs:
            for arm in ARMS:
                if (qid, arm) not in selected:
                    verdicts.setdefault(qid, {})[arm] = brow[qid][arm]["judge"]
        ood_ids = [qid for qid in eqs if _is_ood(qid, run)]
    else:
        ood_ids = [qid for qid in eqs if _apply_out_of_domain_rule(qid, run, verdicts)]
    blocked = [qid for qid in eqs if ((run["results"][qid].get("graphrag") or {}).get("trace") or {}).get("blocked_result")]

    questions = []
    for qid, q in eqs.items():
        row = _row_head(qid, q)
        for arm in ARMS:
            a = run["results"][qid].get(arm) or {}
            row[arm] = {**{k: v for k, v in a.items()}, "judge": verdicts.get(qid, {}).get(arm)}
        questions.append(row)
    counts = {arm: sum(1 for r in questions if (r[arm]["judge"] or {}).get("verdict") == "correct") for arm in ARMS}
    meta = {k: (_mask(v) if isinstance(v, str) else v) for k, v in run["meta"].items()}
    meta["collections"] = [{k: (_mask(v) if isinstance(v, str) else v) for k, v in c.items()} for c in run["meta"].get("collections") or []]
    judged_at = started
    if partial:
        bm = base.get("meta") or {}
        judged_at = bm.get("judged_at")  # the base full judge; each partial re-judge is listed in judge_runs
        meta["judge_runs"] = (bm.get("judge_runs") or [{"judged_at": bm.get("judged_at"), "ids": "all", "arms": list(ARMS)}]) + [
            {"judged_at": started, "ids": sel_ids, "arms": list(sel_arms), "reused_cells": 2 * len(eqs) - len(selected)}]
    doc = {
        "meta": {
            **meta, "eq_version": eq_doc["meta"]["version"], "judged_at": judged_at,
            "judge": {"framework": "ADK LlmAgent (output_schema)", "model": f"{JUDGE_MODEL} (global)",
                      "temperature": 0, "instruction": JUDGE_INSTRUCTION},
            "rules": {"out_of_domain": (eq_doc.get("protocol") or {}).get("scoring", {}).get("out_of_domain_rule")},
            "note": "라이브 시연용 정적 비교. 점수 없음 — 맞음/틀림과 틀린 부분만. 정답 기준은 eval_questions.yaml gold_answer.",
        },
        "summary": {"total": len(questions), "correct": counts,
                    "rule_applied": {"out_of_domain": ood_ids},
                    "question_unchecked": unchecked,
                    "errors": sum(1 for r in questions for arm in ARMS if (r[arm]["judge"] or {}).get("verdict") not in ("correct", "incorrect"))},
        "questions": questions,
    }
    reuse_note = ""
    if partial:
        # post-check before writing: every reused cell serialises exactly as in the base file
        same = sum(1 for r in questions for arm in ARMS if (r["id"], arm) not in selected
                   and json.dumps(r[arm], ensure_ascii=False) == json.dumps(brow[r["id"]][arm], ensure_ascii=False))
        want = 2 * len(eqs) - len(selected)
        if same != want:
            print(f"ABORT: reused cells not byte-identical ({same}/{want}) — nothing written")
            return 1
        reuse_note = f" · partial: judged {sorted(f'{q}/{a}' for q, a in selected)} · reused cells byte-identical {same}/{want}"
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    leaks = sum(OUT_PATH.read_text(encoding="utf-8").count(m) for m in MASK)
    n = len(questions)
    print(f"wrote {OUT_PATH.relative_to(ROOT)} · eq v{eq_doc['meta']['version']} · correct GraphRAG {counts['graphrag']}/{n} · RAG {counts['rag']}/{n} · "
          f"out_of_domain rule {ood_ids} · graphrag blocked {blocked} · question unchecked {len(unchecked)} · "
          f"judge errors {doc['summary']['errors']} · project-id leaks {leaks}{reuse_note}")
    return 0 if doc["summary"]["errors"] == 0 and leaks == 0 else 1


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect", help="ask EQs to the deployed engines (full, or partial with --arms/--ids)")
    c.add_argument("--arms", default="graphrag,rag", help="comma list: graphrag,rag")
    c.add_argument("--ids", default="", help="comma list of EQ ids (default: all)")
    j = sub.add_parser("judge", help="ADK judge over compare_run.json -> okf_veri_web/data/eq_compare.json (full, or partial with --arms/--ids)")
    j.add_argument("--arms", default="graphrag,rag", help="comma list: graphrag,rag")
    j.add_argument("--ids", default="", help="comma list of EQ ids: re-judge only these cells, reuse every other verdict (default: all)")
    a = ap.parse_args()
    arms = [x.strip() for x in a.arms.split(",") if x.strip()]
    if not arms or set(arms) - {"graphrag", "rag"}:
        ap.error("--arms must be graphrag and/or rag")
    ids = [x.strip() for x in a.ids.split(",") if x.strip()]
    if a.cmd == "collect":
        sys.exit(cmd_collect(arms, ids))
    sys.exit(cmd_judge(ids, arms))
