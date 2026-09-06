"""Application-boundary tests for the private pilot access gate: proves the
gate actually blocks ui/app.py's real screens/functionality, not just that
the underlying comparison logic is correct (see test_pilot_access.py for
that). Offline only -- no real OpenAI call is made or possible here since
authenticated tests only need to reach the setup screen (Screen A), which
makes no model call until its own button is clicked.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "ui" / "app.py"
ACCESS_CODE_ENV_VAR = "AMMU_PILOT_ACCESS_CODE"


@pytest.fixture(autouse=True)
def _reset_streamlit_resource_cache():
    """See tests/test_ui_screen_c.py for why this is needed."""
    import streamlit as st

    st.cache_resource.clear()
    yield


def test_gate_blocks_when_access_code_is_configured_but_not_entered(monkeypatch):
    monkeypatch.setenv(ACCESS_CODE_ENV_VAR, "the-real-code")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-not-real")

    at = AppTest.from_file(str(APP_PATH))
    at.run()

    assert not at.exception
    assert at.title[0].value == "Private Pilot"
    assert not any("Start reviewing my assignment" in b.label for b in at.button)


def test_unauthenticated_session_cannot_trigger_review_calls(monkeypatch, tmp_path):
    monkeypatch.setenv(ACCESS_CODE_ENV_VAR, "the-real-code")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-not-real")
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(sessions_dir))

    at = AppTest.from_file(str(APP_PATH))
    at.run()

    assert not at.exception
    # get_store() is never reached while unauthenticated -- no SessionStore
    # is constructed, so the directory it would create never appears.
    assert not sessions_dir.exists()
    assert not any(ta.label == "Your draft" for ta in at.text_area)


def test_gate_rejects_an_incorrect_code(monkeypatch, caplog):
    monkeypatch.setenv(ACCESS_CODE_ENV_VAR, "the-real-code")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-not-real")

    at = AppTest.from_file(str(APP_PATH))
    at.run()
    at.text_input[0].input("a-wrong-guess")
    at.run()
    with caplog.at_level(logging.DEBUG):
        at.button[0].click()
        at.run()

    assert not at.exception
    assert at.title[0].value == "Private Pilot"
    assert "pilot_authenticated" not in at.session_state
    assert any("isn't right" in e.value for e in at.error)
    assert "a-wrong-guess" not in caplog.text
    assert "the-real-code" not in caplog.text


def test_gate_allows_access_with_the_correct_code(monkeypatch):
    monkeypatch.setenv(ACCESS_CODE_ENV_VAR, "the-real-code")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-not-real")

    at = AppTest.from_file(str(APP_PATH))
    at.run()
    at.text_input[0].input("the-real-code")
    at.run()
    at.button[0].click()
    at.run()

    assert not at.exception
    assert at.session_state["pilot_authenticated"] is True
    # The code itself must not linger in session state once authenticated.
    assert "pilot_access_code_input" not in at.session_state
    assert at.title[0].value == "Start a new assignment"


def test_gate_fails_closed_when_access_code_is_not_configured(monkeypatch):
    monkeypatch.delenv(ACCESS_CODE_ENV_VAR, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-not-real")

    at = AppTest.from_file(str(APP_PATH))
    at.run()

    assert not at.exception
    assert any("isn't set up yet" in e.value for e in at.error)
    assert not at.title  # the "Private Pilot" form itself must not render
    assert not at.text_input
    assert not at.button


def test_authenticated_session_reaches_existing_application_flow(monkeypatch):
    monkeypatch.setenv(ACCESS_CODE_ENV_VAR, "the-real-code")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-not-real")

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.run()

    assert not at.exception
    assert at.title[0].value == "Start a new assignment"


def test_missing_openai_api_key_fails_gracefully_after_authentication(monkeypatch):
    monkeypatch.setenv(ACCESS_CODE_ENV_VAR, "the-real-code")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.run()

    assert not at.exception
    assert any("isn't set up yet" in e.value for e in at.error)
    assert not any(t.value == "Start a new assignment" for t in at.title)
