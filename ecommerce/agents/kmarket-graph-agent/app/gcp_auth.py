"""OAuth access token for the REST adapters (BigQuery jobs.query, Dataplex, GCS reads).

ADC (`google.auth.default`) first, retried with backoff: right after a deploy, a cold Agent Runtime
instance can fail its first metadata-server call (2026-09-28 02:09Z, 1 of 21 requests). The
`gcloud` CLI is a workstation-only fallback, used only when it is on PATH. Agent Runtime has no
gcloud, so there the original ADC error is logged and raised instead of the misleading
"[Errno 2] No such file or directory: 'gcloud'".
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from typing import Any

import google.auth
import google.auth.transport.requests

_log = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]
ADC_ATTEMPTS = int(os.environ.get("STARLIGHT_ADC_ATTEMPTS", "3"))
ADC_BACKOFF_S = float(os.environ.get("STARLIGHT_ADC_BACKOFF_S", "0.5"))

_LOCK = threading.Lock()
_CREDS: Any = None


def _adc_token() -> str:
    global _CREDS
    with _LOCK:
        if _CREDS is None:
            _CREDS, _ = google.auth.default(scopes=SCOPES)
        if not _CREDS.valid:
            _CREDS.refresh(google.auth.transport.requests.Request())
        if not _CREDS.token:
            raise RuntimeError("ADC credentials returned an empty token")
        return str(_CREDS.token)


def _gcloud_token(gcloud: str) -> str:
    env = dict(
        os.environ,
        CLOUDSDK_CONTEXT_AWARE_USE_CLIENT_CERTIFICATE="false",
        GOOGLE_API_USE_CLIENT_CERTIFICATE="false",
        GOOGLE_API_USE_MTLS_ENDPOINT="never",
    )
    r = subprocess.run(
        [gcloud, "auth", "print-access-token"], capture_output=True, text=True, timeout=10, env=env
    )
    token = r.stdout.strip()
    if r.returncode != 0 or not token:
        raise RuntimeError(f"gcloud auth print-access-token failed (rc={r.returncode}): {r.stderr.strip()[:300]}")
    return token


def access_token() -> str:
    """Bearer token: ADC with retries, then gcloud only if installed; otherwise the ADC error."""
    global _CREDS
    last: Exception | None = None
    for attempt in range(1, ADC_ATTEMPTS + 1):
        try:
            return _adc_token()
        except Exception as exc:  # noqa: BLE001 — logged and re-raised below
            last = exc
            _log.warning("ADC token attempt %d/%d failed: %r", attempt, ADC_ATTEMPTS, exc)
            with _LOCK:
                _CREDS = None  # re-run google.auth.default() on the next attempt
            if attempt < ADC_ATTEMPTS:
                time.sleep(ADC_BACKOFF_S * (2 ** (attempt - 1)))
    gcloud = shutil.which("gcloud")
    if gcloud:
        _log.warning("ADC unavailable after %d attempts; using the gcloud CLI fallback", ADC_ATTEMPTS)
        return _gcloud_token(gcloud)
    _log.error("ADC unavailable after %d attempts and gcloud is not on PATH: %r", ADC_ATTEMPTS, last)
    raise RuntimeError(f"no access token: ADC failed after {ADC_ATTEMPTS} attempts ({last!r})") from last
