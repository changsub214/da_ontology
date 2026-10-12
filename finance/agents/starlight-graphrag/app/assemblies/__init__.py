"""Unified assembly for the Starlight GraphRAG agent.

There is no artificial `product` vs `eval_arm` split: this single unified GraphRAG agent
is both the customer-facing agent and the GraphRAG arm in the RAG-vs-GraphRAG evaluation.
Swap point: to upgrade to an ADK 2.0 deterministic graph workflow later, update `build` here
without changing `services/` or `tools/`.
"""

from __future__ import annotations

from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types

from app import callbacks as cb
from app.config import Settings
from app.prompts import graphrag_instruction
from app.tools import GRAPHRAG_TOOLS


def build(settings: Settings, *, name: str, model: str) -> Agent:
    return Agent(
        name=name,
        model=Gemini(model=model, retry_options=types.HttpRetryOptions(attempts=3)),
        instruction=graphrag_instruction(tool_budget=settings.tool_budget),
        tools=list(GRAPHRAG_TOOLS),
        generate_content_config=types.GenerateContentConfig(temperature=0, seed=20260927),
        before_agent_callback=cb.BEFORE_AGENT,
        before_tool_callback=cb.BEFORE_TOOL,
        after_tool_callback=cb.AFTER_TOOL,
        after_model_callback=cb.AFTER_MODEL,
    )
