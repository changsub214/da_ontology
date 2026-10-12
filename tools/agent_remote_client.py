#!/usr/bin/env python3
"""Module 05 remote adapter: call the deployed Agent Runtime `starlight-graphrag` with the same
contract as the local `engine.execute_agent_chat(data, on_stage)`.

Selected by `tools/agent_chat_engine.py` when `STARLIGHT_AGENT_MODE=remote`, so
`tools/studio_server.py` and the web UI stay unchanged.

Mapping (remote root agent = `app.orchestrator.agent.Module05OrchestratorAgent`):
  - event `custom_metadata.type == "stage"`            -> `on_stage(text)`
  - event `custom_metadata.type == "module05_result"`  -> result dict (metadata + `answer_markdown`
                                                          from the event text)
  - event with `error_code`                             -> raise, as the local engine would

Transport: REST `:streamQuery` (one JSON event per line), stdlib + google-auth only, so a web
image does not need the vertexai SDK or ADK. Sessions are left as created (user decision
2026-09-27: no deletion).

Env:
  STARLIGHT_AGENT_RESOURCE  projects/<n>/locations/<loc>/reasoningEngines/<id>
                            (default: `remote_agent_runtime_id` in agents/starlight-graphrag/deployment_metadata.json)
  STARLIGHT_AGENT_USER_ID   session user id (default: okf_veri_web)
  STARLIGHT_AGENT_TIMEOUT_S read timeout in seconds (default: 300; first call may cold-start ~60s)
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
import time
import urllib.request
from typing import Any, Callable

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEPLOY_META = os.path.join(_ROOT, "finance", "agents", "starlight-graphrag", "deployment_metadata.json")
_KMARKET_DEPLOY_META = os.path.join(_ROOT, "ecommerce", "agents", "kmarket-graph-agent", "deployment_metadata.json")

os.environ.setdefault("GOOGLE_API_USE_CLIENT_CERTIFICATE", "false")
os.environ.setdefault("GOOGLE_API_USE_MTLS_ENDPOINT", "never")

_log = logging.getLogger(__name__)
_CREDS_LOCK = threading.Lock()
_CREDS: Any = None


def agent_resource() -> str:
    res = os.environ.get("STARLIGHT_AGENT_RESOURCE")
    if res:
        return res
    with open(_DEPLOY_META, "r", encoding="utf-8") as f:
        return json.load(f)["remote_agent_runtime_id"]


def kmarket_agent_resource() -> str:
    res = os.environ.get("KMARKET_AGENT_RESOURCE")
    if res:
        return res
    with open(_KMARKET_DEPLOY_META, "r", encoding="utf-8") as f:
        return json.load(f)["remote_agent_runtime_id"]


def _access_token() -> str:
    """ADC with retries (cold metadata server); gcloud only when on PATH (workstations).

    Same policy as agents/starlight-graphrag/app/gcp_auth.py, kept self-contained so a web image
    needs google-auth only. On Cloud Run there is no gcloud, so the ADC error is raised as is.
    """
    global _CREDS
    attempts = int(os.environ.get("STARLIGHT_ADC_ATTEMPTS", "3"))
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            import google.auth
            import google.auth.transport.requests

            with _CREDS_LOCK:
                if _CREDS is None:
                    _CREDS, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
                if not _CREDS.valid:
                    _CREDS.refresh(google.auth.transport.requests.Request())
                if _CREDS.token:
                    return str(_CREDS.token)
                raise RuntimeError("ADC credentials returned an empty token")
        except Exception as exc:  # noqa: BLE001 — logged and re-raised below
            last = exc
            _log.warning("ADC token attempt %d/%d failed: %r", attempt, attempts, exc)
            with _CREDS_LOCK:
                _CREDS = None
            if attempt < attempts:
                time.sleep(0.5 * (2 ** (attempt - 1)))
    gcloud = shutil.which("gcloud")
    if not gcloud:
        raise RuntimeError(f"no access token: ADC failed after {attempts} attempts ({last!r})") from last
    # Workstation fallback.
    env = dict(os.environ, CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE="false")
    r = subprocess.run(
        [gcloud, "auth", "print-access-token"], capture_output=True, text=True, timeout=10, env=env
    )
    token = r.stdout.strip()
    if r.returncode != 0 or not token:
        raise RuntimeError(f"gcloud auth print-access-token failed (rc={r.returncode}): {r.stderr.strip()[:300]}")
    return token


def _execute_stream_query(
    res: str, data: dict[str, Any], on_stage: Callable[[str], None] | None = None
) -> dict[str, Any]:
    location = res.split("/locations/")[1].split("/")[0]
    url = f"https://{location}-aiplatform.googleapis.com/v1/{res}:streamQuery"
    # The remote agent parses a JSON payload from the message text (`{"num", "question"}`).
    message = json.dumps({k: v for k, v in (data or {}).items() if k != "stream"}, ensure_ascii=False)
    body = {
        "class_method": "stream_query",
        "input": {"user_id": os.environ.get("STARLIGHT_AGENT_USER_ID", "okf_veri_web"), "message": message},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {_access_token()}", "Content-Type": "application/json"},
        method="POST",
    )
    timeout = float(os.environ.get("STARLIGHT_AGENT_TIMEOUT_S", "300"))

    result: dict[str, Any] | None = None
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:  # one event per line, delivered as the agent yields
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            ev = json.loads(line)
            if ev.get("error_code"):
                raise RuntimeError(f"{ev.get('error_code')}: {ev.get('error_message') or ''}".strip())
            cm = ev.get("custom_metadata") or {}
            kind = cm.get("type")
            if kind == "stage":
                if on_stage is not None:
                    on_stage(str(cm.get("text", "")))
            elif kind == "module05_result":
                parts = (ev.get("content") or {}).get("parts") or []
                result = {k: v for k, v in cm.items() if k != "type"}
                result["answer_markdown"] = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    if result is None:
        raise RuntimeError(f"remote agent {res} returned no module05_result event")
    return result


def execute_agent_chat(
    data: dict[str, Any], on_stage: Callable[[str], None] | None = None
) -> dict[str, Any]:
    return _execute_stream_query(agent_resource(), data, on_stage=on_stage)


def execute_kmarket_agent_chat(
    data: dict[str, Any], on_stage: Callable[[str], None] | None = None
) -> dict[str, Any]:
    return _execute_stream_query(kmarket_agent_resource(), data, on_stage=on_stage)


__all__ = [
    "agent_resource",
    "kmarket_agent_resource",
    "execute_agent_chat",
    "execute_kmarket_agent_chat",
]
