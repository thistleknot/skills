"""Regression tests for the health_probe CLI reindex fallback.

The probe is meant to run headless from the 5-minute Scheduled Task under
pythonw.exe. A GUI-subsystem parent has no console to inherit, so any child
process it spawns gets a brand-new console window unless explicitly suppressed
— and the CLI reindex path is exactly the failure path that must stay quiet.
"""
from __future__ import annotations

import subprocess
import sys

import pytest

import health_probe as hp

WINDOWS_ONLY = pytest.mark.skipif(sys.platform != "win32", reason="Windows console behaviour")


@WINDOWS_ONLY
def test_cli_reindex_fallback_spawns_no_console(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN202
        captured.update(kwargs)
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="indexed 12", stderr="")

    monkeypatch.setattr(hp, "http_post", lambda *a, **k: None)  # force CLI fallback
    monkeypatch.setattr(hp.subprocess, "run", fake_run)

    assert hp.reindex() is True
    assert captured["creationflags"] == subprocess.CREATE_NO_WINDOW
    assert captured["creationflags"] != 0


def test_cli_reindex_reports_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN202
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")

    monkeypatch.setattr(hp, "http_post", lambda *a, **k: None)
    monkeypatch.setattr(hp.subprocess, "run", fake_run)
    assert hp.reindex() is False


def test_cli_reindex_swallows_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(cmd, **kwargs):  # noqa: ANN001, ANN202
        raise OSError("indexer missing")

    monkeypatch.setattr(hp, "http_post", lambda *a, **k: None)
    monkeypatch.setattr(hp.subprocess, "run", fake_run)
    assert hp.reindex() is False


def test_http_reindex_preferred_over_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    """Happy path never reaches the subprocess at all."""
    def forbidden_run(cmd, **kwargs):  # noqa: ANN001, ANN202
        raise AssertionError("CLI fallback used despite a healthy HTTP reindex")

    monkeypatch.setattr(hp, "http_post", lambda *a, **k: {"total": 12})
    monkeypatch.setattr(hp.subprocess, "run", forbidden_run)
    assert hp.reindex() is True
