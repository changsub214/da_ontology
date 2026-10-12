#!/usr/bin/env python3
"""Module 06 RAG remote adapter: call the deployed Agent Runtime `starlight-rag-agent`
(`SequentialAgent`: `rag_step` -> `sql_step` -> `answer_step`) and emit live stage updates
plus a structured result dict for `/api/rag/chat` and `/api/rag/chat/stream`.

Reuses `agent_remote_client._access_token` (ADC with retries, workstation `gcloud` fallback).
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from typing import Any, Callable

from agent_remote_client import _access_token

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEPLOY_META = os.path.join(_ROOT, "finance", "agents", "starlight-rag-agent", "deployment_metadata.json")
_KMARKET_DEPLOY_META = os.path.join(_ROOT, "ecommerce", "agents", "kmarket-rag-agent", "deployment_metadata.json")
_MASK_PROJECT_ID = "finance-ontology-changseop"
_MASK_PROJECT_NUMBER = "567090080191"


def rag_agent_resource() -> str:
    res = os.environ.get("STARLIGHT_RAG_AGENT_RESOURCE")
    if res:
        return res
    with open(_DEPLOY_META, "r", encoding="utf-8") as f:
        return json.load(f)["remote_agent_runtime_id"]


def kmarket_rag_agent_resource() -> str:
    res = os.environ.get("KMARKET_RAG_AGENT_RESOURCE")
    if res:
        return res
    with open(_KMARKET_DEPLOY_META, "r", encoding="utf-8") as f:
        return json.load(f)["remote_agent_runtime_id"]


def _mask(s: str, project_alias: str = "starlight-gcp-project") -> str:
    if not s:
        return ""
    return (
        s.replace(f"{_MASK_PROJECT_ID}.", "")
        .replace(_MASK_PROJECT_ID, project_alias)
        .replace(_MASK_PROJECT_NUMBER, "000000000000")
    )


def _execute_rag_stream_query(
    res: str,
    data: dict[str, Any],
    on_stage: Callable[[str], None] | None = None,
    *,
    agent_label: str = "starlight-rag-agent",
    dataset_label: str = "starlight_bank.*",
    project_alias: str = "starlight-gcp-project",
    max_chunks: int = 8,
) -> dict[str, Any]:
    question = str((data or {}).get("question") or "").strip()
    if not question:
        raise ValueError("question is required")

    location = res.split("/locations/")[1].split("/")[0]
    url = f"https://{location}-aiplatform.googleapis.com/v1/{res}:streamQuery"
    body = {
        "class_method": "stream_query",
        "input": {
            "user_id": os.environ.get("STARLIGHT_RAG_USER_ID", "okf_veri_web"),
            "message": question,
        },
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"},
        method="POST",
    )
    timeout = float(os.environ.get("STARLIGHT_RAG_TIMEOUT_S", "300"))
    t0 = time.time()

    if on_stage is not None:
        on_stage(f"원격 RAG 엔진 연결 중 ({agent_label} · 콜드 스타트 시 최대 1분)…")

    rag_calls = 0
    sql_calls = 0
    rag_query = ""
    rag_chunks: list[dict[str, Any]] = []
    sql = ""
    sql_status = ""
    answer = ""
    sent_answer_stage = False

    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            ev = json.loads(line)
            if ev.get("error_code"):
                raise RuntimeError(f"{ev.get('error_code')}: {ev.get('error_message') or ''}".strip())
            author = ev.get("author") or ""
            for p in (ev.get("content") or {}).get("parts") or []:
                if not isinstance(p, dict):
                    continue
                fc = p.get("function_call")
                fr = p.get("function_response")
                if fc and fc.get("name") == "vertex_rag_search":
                    rag_calls += 1
                    rag_query = str((fc.get("args") or {}).get("query", ""))
                    if on_stage is not None:
                        on_stage(f"① Vertex AI RAG 검색 중: {rag_query[:64]}…")
                elif fr and fr.get("name") == "vertex_rag_search":
                    ctxs = (fr.get("response") or {}).get("contexts") or []
                    rag_chunks = [
                        {
                            "doc_id": c.get("doc_id"),
                            "source": c.get("source"),
                            "score": c.get("score"),
                            "text": _mask((c.get("text") or "")[:400], project_alias),
                        }
                        for c in ctxs[:max_chunks]
                    ]
                    docs = sorted({str(c.get("doc_id") or "") for c in rag_chunks if c.get("doc_id")})
                    if on_stage is not None:
                        doc_label = ", ".join(docs) if docs else "0건"
                        on_stage(f"① RAG 청크 {len(rag_chunks)}건 수집 (문서 {doc_label}) → ② BigQuery SQL 생성 중…")
                elif fc and fc.get("name") == "execute_sql":
                    sql_calls += 1
                    sql = _mask(str((fc.get("args") or {}).get("query", "")), project_alias)
                    if on_stage is not None:
                        on_stage(f"② BigQuery SQL 실행 중 ({dataset_label} · 읽기 전용)…")
                elif fr and fr.get("name") == "execute_sql":
                    sql_status = _mask(str((fr.get("response") or {}).get("status", "")), project_alias)
                    if on_stage is not None:
                        on_stage(f"② SQL 완료 ({sql_status or 'SUCCESS'}) → ③ 최종 답변 작성 중…")
                if author == "answer_step" and p.get("text"):
                    if not sent_answer_stage and on_stage is not None:
                        sent_answer_stage = True
                        on_stage("③ 최종 답변 생성 중…")
                    answer += str(p["text"])

    return {
        "ok": True,
        "question": question,
        "answer_markdown": _mask(answer, project_alias),
        "rag_calls": rag_calls,
        "sql_calls": sql_calls,
        "rag_query": _mask(rag_query, project_alias),
        "rag_chunks": rag_chunks,
        "sql": sql,
        "sql_status": sql_status,
        "elapsed_s": round(time.time() - t0, 1),
    }


def execute_rag_chat(
    data: dict[str, Any], on_stage: Callable[[str], None] | None = None
) -> dict[str, Any]:
    return _execute_rag_stream_query(
        rag_agent_resource(),
        data,
        on_stage=on_stage,
        agent_label="starlight-rag-agent",
        dataset_label="starlight_bank.*",
        project_alias="starlight-gcp-project",
    )


def execute_kmarket_rag_chat(
    data: dict[str, Any], on_stage: Callable[[str], None] | None = None
) -> dict[str, Any]:
    return _execute_rag_stream_query(
        kmarket_rag_agent_resource(),
        data,
        on_stage=on_stage,
        agent_label="kmarket-rag-agent",
        dataset_label="kmarket_ontology.*",
        project_alias="kmarket-gcp-project",
        max_chunks=3,
    )


__all__ = [
    "rag_agent_resource",
    "kmarket_rag_agent_resource",
    "execute_rag_chat",
    "execute_kmarket_rag_chat",
]
