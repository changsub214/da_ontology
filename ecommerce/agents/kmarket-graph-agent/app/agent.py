# ruff: noqa
import os
from google.adk.apps import App
from app.orchestrator.agent import Module05OrchestratorAgent

MODEL = os.environ.get("STARLIGHT_MODEL", "gemini-3.8-flash")

root_agent = Module05OrchestratorAgent(
    name="kmarket_graph_agent",
    description="K마켙(K-Market) 온톨로지 Graph 전문 에이전트 (Module 05 결정적 오케스트레이터)",
)

app = App(
    root_agent=root_agent,
    name="app",
)
