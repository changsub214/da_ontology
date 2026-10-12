"""Token policy guards (runbook S13 pitfall, 2026-09-28): a cold Agent Runtime instance must retry
ADC and must never shell out to a gcloud CLI that is not installed."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app import gcp_auth


class _Creds:
    def __init__(self, fail_refreshes: int) -> None:
        self.fail_refreshes = fail_refreshes
        self.valid = False
        self.token = None

    def refresh(self, _request) -> None:
        if self.fail_refreshes > 0:
            self.fail_refreshes -= 1
            raise OSError("metadata server not ready")
        self.valid, self.token = True, "adc-token"


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(gcp_auth, "_CREDS", None)
    monkeypatch.setattr(gcp_auth, "ADC_BACKOFF_S", 0.0)
    monkeypatch.setattr(gcp_auth, "ADC_ATTEMPTS", 3)


def test_adc_retry_recovers_without_gcloud(monkeypatch) -> None:
    creds = _Creds(fail_refreshes=2)
    monkeypatch.setattr(gcp_auth.google.auth, "default", lambda scopes: (creds, "p"))
    monkeypatch.setattr(gcp_auth.shutil, "which", lambda _: pytest.fail("gcloud must not be looked up"))
    assert gcp_auth.access_token() == "adc-token"


def test_no_gcloud_raises_adc_error(monkeypatch) -> None:
    creds = _Creds(fail_refreshes=99)
    monkeypatch.setattr(gcp_auth.google.auth, "default", lambda scopes: (creds, "p"))
    monkeypatch.setattr(gcp_auth.shutil, "which", lambda _: None)
    monkeypatch.setattr(gcp_auth.subprocess, "run", lambda *a, **k: pytest.fail("gcloud must not run"))
    with pytest.raises(RuntimeError, match="metadata server not ready"):
        gcp_auth.access_token()


def test_gcloud_fallback_only_when_installed(monkeypatch) -> None:
    def no_adc(scopes):
        raise gcp_auth.google.auth.exceptions.DefaultCredentialsError("no ADC")

    calls = []

    def fake_run(cmd, **_):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout="cli-token\n", stderr="")

    monkeypatch.setattr(gcp_auth.google.auth, "default", no_adc)
    monkeypatch.setattr(gcp_auth.shutil, "which", lambda _: "/usr/bin/gcloud")
    monkeypatch.setattr(gcp_auth.subprocess, "run", fake_run)
    assert gcp_auth.access_token() == "cli-token"
    assert calls == [["/usr/bin/gcloud", "auth", "print-access-token"]]


def test_gcloud_failure_is_not_an_empty_token(monkeypatch) -> None:
    def no_adc(scopes):
        raise gcp_auth.google.auth.exceptions.DefaultCredentialsError("no ADC")

    monkeypatch.setattr(gcp_auth.google.auth, "default", no_adc)
    monkeypatch.setattr(gcp_auth.shutil, "which", lambda _: "/usr/bin/gcloud")
    monkeypatch.setattr(
        gcp_auth.subprocess, "run", lambda *a, **k: SimpleNamespace(returncode=1, stdout="", stderr="login required")
    )
    with pytest.raises(RuntimeError, match="login required"):
        gcp_auth.access_token()


def test_adapters_have_no_direct_gcloud_calls() -> None:
    from pathlib import Path

    app = Path(gcp_auth.__file__).resolve().parent
    offenders = [
        str(p.relative_to(app))
        for p in app.rglob("*.py")
        if p.name != "gcp_auth.py" and '"gcloud"' in p.read_text(encoding="utf-8")
    ]
    assert offenders == [], f"use app.gcp_auth.access_token() instead of calling gcloud: {offenders}"
