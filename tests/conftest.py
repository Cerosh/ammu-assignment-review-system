"""Shared pytest fixtures.

Autouse: point AMMU_SESSIONS_DIR / AMMU_TELEMETRY_DIR at a per-test tmp_path
so no test -- including one that doesn't explicitly construct a
SessionStore/TelemetryStore with its own base_dir -- can ever write to the
real project data/ directory. A test that already passes its own
``base_dir=tmp_path`` is unaffected: that ignores the env var entirely.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _isolate_default_data_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(tmp_path / "sessions"))
    monkeypatch.setenv("AMMU_TELEMETRY_DIR", str(tmp_path / "telemetry"))
