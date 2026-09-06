"""Tests for the private pilot access gate (pure logic; no Streamlit).

See ui/app.py::render_access_gate and tests/test_ui_pilot_access.py for the
Streamlit-level boundary tests (does the gate actually block the app)."""

from __future__ import annotations

import logging

from ammu_review.pilot_access import ACCESS_CODE_ENV_VAR, check_access_code, get_pilot_access_code


def test_get_pilot_access_code_reads_from_environment(monkeypatch):
    monkeypatch.setenv(ACCESS_CODE_ENV_VAR, "correct-horse-battery-staple")
    assert get_pilot_access_code() == "correct-horse-battery-staple"


def test_get_pilot_access_code_is_none_when_unset(monkeypatch):
    monkeypatch.delenv(ACCESS_CODE_ENV_VAR, raising=False)
    assert get_pilot_access_code() is None


def test_get_pilot_access_code_treats_empty_string_as_unset(monkeypatch):
    # An accidentally-blank env var (e.g. AMMU_PILOT_ACCESS_CODE= with
    # nothing after it) must fail closed too, not silently become "any
    # code matches the empty string".
    monkeypatch.setenv(ACCESS_CODE_ENV_VAR, "")
    assert get_pilot_access_code() is None


def test_check_access_code_accepts_the_correct_code():
    assert check_access_code("letmein", "letmein") is True


def test_check_access_code_rejects_an_incorrect_code():
    assert check_access_code("wrong-guess", "letmein") is False


def test_check_access_code_rejects_a_different_length_guess():
    assert check_access_code("way-too-long-a-guess-to-be-right", "letmein") is False


def test_check_access_code_never_logs_the_codes(caplog):
    with caplog.at_level(logging.DEBUG):
        check_access_code("some-guess", "the-real-code")
    assert "some-guess" not in caplog.text
    assert "the-real-code" not in caplog.text


def test_env_example_documents_the_access_code_as_a_placeholder_only():
    from pathlib import Path

    env_example = Path(__file__).resolve().parents[1] / ".env.example"
    text = env_example.read_text()
    assert "AMMU_PILOT_ACCESS_CODE=" in text
    # A real committed example must never carry an actual value.
    for line in text.splitlines():
        if line.strip().startswith("AMMU_PILOT_ACCESS_CODE="):
            assert line.strip() == "# AMMU_PILOT_ACCESS_CODE=" or line.strip() == "AMMU_PILOT_ACCESS_CODE="


def test_env_example_never_contains_the_real_local_openai_key():
    from pathlib import Path

    env_example_text = (Path(__file__).resolve().parents[1] / ".env.example").read_text()
    # Real OpenAI keys are always much longer than the placeholder line
    # ("OPENAI_API_KEY=") -- this guards against ever accidentally pasting
    # a real value into the committed example file.
    for line in env_example_text.splitlines():
        if line.startswith("OPENAI_API_KEY="):
            assert line == "OPENAI_API_KEY="
