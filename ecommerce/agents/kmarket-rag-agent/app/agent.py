# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Starlight RAG Agent — RAG arm of the RAG-vs-GraphRAG evaluation (ADR 0004 · 0011,
agents/design/rag_agent_v0.yaml v0.2.0).

ADK only. A SequentialAgent forces exactly one retrieval and one SQL execution per turn:
  1. rag_step    — ADK VertexAiRagRetrieval over the RAG Engine corpus, used through its function-call path
                   (mode=ANY + one-call guard + skip_summarization). Gemini built-in retrieval was dropped because
                   the model may decide not to search (local smoke 14:59Z: 0/4 turns grounded).
  2. sql_step    — BigQueryToolset `execute_sql` (write blocked). tool_config mode=ANY forces the call,
                   a before_tool_callback rejects any second call, and skip_summarization ends the step.
  3. answer_step — writes the final answer from the question, the retrieved chunks and the SQL rows.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
from typing import Any

import google.auth
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.integrations.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.integrations.bigquery.config import BigQueryToolConfig, WriteMode
from google.adk.models import Gemini, LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval
from google.adk.tools.tool_context import ToolContext
from google.genai import types

os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
# Model endpoint is pinned to global (user decision 14:47Z), also on Agent Runtime where the runtime region is
# injected. The RAG corpus stays in us-central1 and is addressed by its full resource name.
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"

MODEL = "gemini-3.8-flash"
SEED = 20260927

# Agent Runtime injects GOOGLE_CLOUD_PROJECT as the project number; IDs used in SQL text need the ID (DR-07).
PROJECT_ID = os.environ.get("STARLIGHT_PROJECT_ID", "finance-ontology-changseop")
PROJECT_NUMBER = os.environ.get("STARLIGHT_PROJECT_NUMBER", "567090080191")
RAG_CORPUS = os.environ.get("KMARKET_RAG_CORPUS") or os.environ.get("STARLIGHT_RAG_CORPUS") or "projects/567090080191/locations/us-central1/ragCorpora/178446339141533696"  # projects/<n>/locations/us-central1/ragCorpora/<id>
BQ_LOCATION = os.environ.get("STARLIGHT_DATA_LOCATION", "us-central1")
RAG_TOP_K = int(os.environ.get("KMARKET_RAG_TOP_K", os.environ.get("STARLIGHT_RAG_TOP_K", "3")))

SCHEMA_CARD = (pathlib.Path(__file__).parent / "data" / "schema_card.md").read_text(encoding="utf-8")

# Keys in session state (one place).
K_QUESTION, K_EVIDENCE, K_CHUNKS = "question", "rag_evidence", "rag_chunks"
K_RAG_CALLS, K_RAG_QUERY = "rag_calls", "rag_query"
K_SQL_CALLS, K_SQL, K_SQL_RESULT = "sql_calls", "sql_query", "sql_result"

ROLE = (
    "당신은 K마켙(K-Market)의 초개인화 추천·MD 마진관리·파트너 판촉비 정산·CS 반품심사 담당자를 돕는 분석 보조입니다. "
    "근거가 없는 내용은 추측하지 말고 '근거 문서에서 확인되지 않음'이라고 밝힙니다."
)
CITATION_RULE = "인용은 [문서 NN p.X] 또는 [문서 NN 제N조] 형식으로 표기합니다 (NN = 파일명 앞 두 자리 01–10)."


def _gen_config(**extra: Any) -> types.GenerateContentConfig:
    return types.GenerateContentConfig(temperature=0, seed=SEED, **extra)


def _model() -> Gemini:
    return Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3))


def _mask(text: str) -> str:
    return (
        text.replace(f"{PROJECT_ID}.", "")
        .replace(PROJECT_ID, "kmarket-gcp-project")
        .replace(PROJECT_NUMBER, "000000000000")
    )


def _force(fn_name: str) -> types.GenerateContentConfig:
    return _gen_config(
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(mode="ANY", allowed_function_names=[fn_name])
        )
    )


# ---------------------------------------------------------------------------
# root: capture the question (plain text or the GraphRAG-style JSON payload {"question": ...})
# ---------------------------------------------------------------------------
def capture_question(callback_context: CallbackContext) -> None:
    text = ""
    uc = callback_context.user_content
    if uc and uc.parts:
        text = "".join(p.text or "" for p in uc.parts).strip()
    if text.startswith("{"):
        try:
            text = str(json.loads(text).get("question") or text)
        except (ValueError, AttributeError):
            pass
    st = callback_context.state
    st[K_QUESTION] = text
    st[K_RAG_CALLS] = 0
    st[K_RAG_QUERY] = ""
    st[K_CHUNKS] = []
    st[K_EVIDENCE] = ""
    st[K_SQL_CALLS] = 0
    st[K_SQL] = ""
    st[K_SQL_RESULT] = ""


# ---------------------------------------------------------------------------
# 1. rag_step — exactly one retrieval
# ---------------------------------------------------------------------------
class ForcedRagRetrieval(VertexAiRagRetrieval):
    """VertexAiRagRetrieval that always exposes a function declaration and keeps source name / page / score."""

    async def process_llm_request(self, *, tool_context: ToolContext, llm_request: Any) -> None:
        # Skip VertexAiRagRetrieval's built-in-retrieval branch; use BaseTool's function-declaration path.
        await super(VertexAiRagRetrieval, self).process_llm_request(tool_context=tool_context, llm_request=llm_request)

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        from google.adk.dependencies.vertexai import rag  # ADK's own RAG dependency (same as the parent class)

        query = args.get("query")
        if not isinstance(query, str):
            raise ValueError("vertex_rag_search requires a string 'query'.")
        resp = await asyncio.to_thread(
            rag.retrieval_query,
            text=query,
            rag_corpora=self.vertex_rag_store.rag_corpora,
            similarity_top_k=self.vertex_rag_store.similarity_top_k,
        )
        out = []
        for c in resp.contexts.contexts:
            name = c.source_display_name or os.path.basename(c.source_uri or "")
            ps = getattr(getattr(c, "chunk", None), "page_span", None)
            first = getattr(ps, "first_page", 0) or 0
            last = getattr(ps, "last_page", 0) or 0
            out.append({
                "doc_id": name[:2], "source": name, "score": round(float(c.score or 0), 4),
                "pages": (f"{first}" if first == last else f"{first}-{last}") if first else "", "text": c.text,
            })
        return {"status": "SUCCESS", "query": query, "contexts": out}


def rag_instruction(_ctx: Any) -> str:
    return (
        f"{ROLE}\n\n"
        "질문에 답하는 데 필요한 규정·보고서·내규 근거를 찾기 위해 vertex_rag_search 를 **정확히 한 번** 호출하세요. "
        "query 는 질문의 핵심 용어(기관명·규정명·조문·수치 개념)를 담은 한국어 검색문으로 작성합니다."
    )


def allow_one_rag(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> dict | None:
    n = int(tool_context.state.get(K_RAG_CALLS, 0))
    if n >= 1:
        return {"status": "ERROR", "error_details": "검색은 턴당 1회만 허용됩니다 (RAG 1 · SQL 1 고정)."}
    tool_context.state[K_RAG_CALLS] = n + 1
    tool_context.state[K_RAG_QUERY] = str(args.get("query", ""))
    return None


def _format_evidence(chunks: list[dict]) -> str:
    lines = []
    for i, c in enumerate(chunks, 1):
        page = f" p.{c['pages']}" if c.get("pages") else ""
        lines.append(f"[{i}] 문서 {c['doc_id']}{page} ({c['source']}, score {c['score']})\n{c['text'].strip()}")
    return "\n\n".join(lines) if lines else "(검색 결과 없음)"


def store_rag_result(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, tool_response: Any) -> dict | None:
    if isinstance(tool_response, dict) and tool_response.get("status") == "SUCCESS" and not tool_context.state.get(K_CHUNKS):
        chunks = tool_response.get("contexts", [])
        tool_context.state[K_CHUNKS] = [{**c, "text": c["text"][:1200]} for c in chunks]
        tool_context.state[K_EVIDENCE] = _format_evidence(chunks)
    tool_context.actions.skip_summarization = True  # end the step right after the single call
    return None


rag_step = LlmAgent(
    name="rag_step",
    model=_model(),
    instruction=rag_instruction,
    tools=[
        ForcedRagRetrieval(
            name="vertex_rag_search",
            description="K마켙 공정거래·전자상거래·개보위 법령 및 사내 내규 PDF 10종 코퍼스(RAG Engine) 의미 검색. query: 한국어 검색문.",
            rag_corpora=[RAG_CORPUS] if RAG_CORPUS else None,
            similarity_top_k=RAG_TOP_K,
        )
    ],
    generate_content_config=_force("vertex_rag_search"),
    before_tool_callback=allow_one_rag,
    after_tool_callback=store_rag_result,
)


# ---------------------------------------------------------------------------
# 2. sql_step — exactly one execute_sql
# ---------------------------------------------------------------------------
def sql_instruction(ctx: Any) -> str:
    st = ctx.state
    return (
        f"{ROLE}\n\n"
        "아래 질문에 답하는 데 필요한 원장 수치를 BigQuery 에서 **한 번의 SELECT 쿼리**로 조회하세요. "
        "반드시 execute_sql 을 정확히 한 번 호출합니다(재시도 없음). 여러 값이 필요하면 JOIN/서브쿼리/UNION ALL 로 한 쿼리에 담으세요. "
        f"project_id 인자는 `{PROJECT_ID}` 입니다. 원장과 무관한 질문이면 근거 확인용으로 가장 관련 있는 테이블을 조회하세요.\n\n"
        f"## 질문\n{st.get(K_QUESTION, '')}\n\n"
        f"## 문서 검색 결과 (rag_step)\n{st.get(K_EVIDENCE, '')}\n\n"
        f"## 스키마\n{SCHEMA_CARD}"
    )


def allow_one_sql(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext) -> dict | None:
    n = int(tool_context.state.get(K_SQL_CALLS, 0))
    if n >= 1:
        return {"status": "ERROR", "error_details": "SQL 은 턴당 1회만 허용됩니다 (RAG 1 · SQL 1 고정)."}
    tool_context.state[K_SQL_CALLS] = n + 1
    tool_context.state[K_SQL] = _mask(str(args.get("query", "")))
    return None


def store_sql_result(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, tool_response: Any) -> dict | None:
    if not tool_context.state.get(K_SQL_RESULT):
        tool_context.state[K_SQL_RESULT] = _mask(json.dumps(tool_response, ensure_ascii=False, default=str)[:20000])
    tool_context.actions.skip_summarization = True  # end the step right after the single call
    return None


bq_toolset = BigQueryToolset(
    credentials_config=BigQueryCredentialsConfig(
        credentials=google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])[0]
    ),
    bigquery_tool_config=BigQueryToolConfig(
        write_mode=WriteMode.BLOCKED,
        maximum_bytes_billed=2 * 1024**3,
        max_query_result_rows=200,
        compute_project_id=PROJECT_ID,
        location=BQ_LOCATION,
    ),
    tool_filter=["execute_sql"],
)

sql_step = LlmAgent(
    name="sql_step",
    model=_model(),
    instruction=sql_instruction,
    include_contents="none",
    tools=[bq_toolset],
    generate_content_config=_force("execute_sql"),
    before_tool_callback=allow_one_sql,
    after_tool_callback=store_sql_result,
)


# ---------------------------------------------------------------------------
# 3. answer_step — final answer, no tools
# ---------------------------------------------------------------------------
def answer_instruction(ctx: Any) -> str:
    st = ctx.state
    return (
        f"{ROLE}\n\n"
        "아래 질문에 대해 문서 검색 결과와 원장 조회 결과만 사용해 최종 답변을 작성하세요. "
        "결론을 먼저 쓰고, 산식이 있으면 수치와 함께 보이며, 근거마다 출처를 표기하세요. "
        f"{CITATION_RULE}\n\n"
        f"## 질문\n{st.get(K_QUESTION, '')}\n\n"
        f"## 문서 검색 결과 (RAG 1회, query: {st.get(K_RAG_QUERY, '')})\n{st.get(K_EVIDENCE, '')}\n\n"
        f"## 원장 조회 (SQL 1회)\n```sql\n{st.get(K_SQL, '')}\n```\n결과: {st.get(K_SQL_RESULT, '')}"
    )


def mask_answer(callback_context: CallbackContext, llm_response: LlmResponse) -> LlmResponse | None:
    content = llm_response.content
    if content and content.parts:
        for p in content.parts:
            if p.text:
                p.text = _mask(p.text)
    return None


answer_step = LlmAgent(
    name="answer_step",
    model=_model(),
    instruction=answer_instruction,
    include_contents="none",
    generate_content_config=_gen_config(),
    after_model_callback=mask_answer,
)


root_agent = SequentialAgent(
    # Keep in sync with agents-cli-manifest.yaml: agents-cli derives this name
    # from the project `name:` recorded there, and telemetry reports it as
    # gen_ai.agent.name. Renaming the agent only here makes the two disagree,
    # and anything selecting traces by name stops finding this agent's.
    name="kmarket_rag_agent",
    sub_agents=[rag_step, sql_step, answer_step],
    before_agent_callback=capture_question,
)

app = App(
    root_agent=root_agent,
    name="app",
)
