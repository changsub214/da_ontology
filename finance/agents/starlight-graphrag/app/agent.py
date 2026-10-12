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

import os

from google.adk.apps import App

from app.orchestrator.agent import Module05OrchestratorAgent


MODEL = os.environ.get("STARLIGHT_MODEL", "gemini-3.8-flash")

# Keep in sync with agents-cli-manifest.yaml: agents-cli derives this name
# from the project `name:` recorded there (`starlight_graphrag`), and telemetry
# reports it as gen_ai.agent.name.
#
# The root agent is the deterministic Module 05 orchestrator
# (`app.orchestrator.engine.execute_agent_chat`) — the exact code path the local
# studio UI (`05 · agent`) runs. It is NOT a free LlmAgent tool loop: the tool
# order/count (validate → ≤3 GQL repairs → 1 graph_query execution → kc_lookup →
# fetch_provision; refuse if no GQL passes, ADR 0016) is fixed in code.
# `app.assemblies.build` (free LlmAgent variant) is kept for tests only.
root_agent = Module05OrchestratorAgent(
    name="starlight_graphrag",
    description="별빛은행 기업여신 GraphRAG 에이전트 (Module 05 결정적 오케스트레이터)",
)

app = App(
    root_agent=root_agent,
    name="app",
)

