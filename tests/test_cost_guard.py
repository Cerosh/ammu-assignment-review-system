"""Tests for the draft/revision submission cost guard (pure logic; no
Streamlit, no model calls). See tests/test_ui_runtime_safety.py for the
application-boundary tests confirming ui/app.py actually enforces this."""

from __future__ import annotations

from ammu_review.cost_guard import (
    DEFAULT_MAX_DRAFTS_PER_ASSIGNMENT,
    MAX_DRAFTS_ENV_VAR,
    get_max_drafts_per_assignment,
    has_reached_draft_limit,
)


def test_default_limit_is_generous_enough_for_normal_use(monkeypatch):
    monkeypatch.delenv(MAX_DRAFTS_ENV_VAR, raising=False)
    assert get_max_drafts_per_assignment() == DEFAULT_MAX_DRAFTS_PER_ASSIGNMENT
    # Understand -> draft -> a couple of genuine revisions is nowhere near
    # the default -- the guard must not get in the way of normal work.
    assert DEFAULT_MAX_DRAFTS_PER_ASSIGNMENT >= 5


def test_configured_limit_is_read_from_the_environment(monkeypatch):
    monkeypatch.setenv(MAX_DRAFTS_ENV_VAR, "3")
    assert get_max_drafts_per_assignment() == 3


def test_non_numeric_configured_value_falls_back_to_default(monkeypatch):
    monkeypatch.setenv(MAX_DRAFTS_ENV_VAR, "not-a-number")
    assert get_max_drafts_per_assignment() == DEFAULT_MAX_DRAFTS_PER_ASSIGNMENT


def test_zero_configured_value_falls_back_to_default_rather_than_blocking_everything(monkeypatch):
    monkeypatch.setenv(MAX_DRAFTS_ENV_VAR, "0")
    assert get_max_drafts_per_assignment() == DEFAULT_MAX_DRAFTS_PER_ASSIGNMENT


def test_negative_configured_value_falls_back_to_default(monkeypatch):
    monkeypatch.setenv(MAX_DRAFTS_ENV_VAR, "-5")
    assert get_max_drafts_per_assignment() == DEFAULT_MAX_DRAFTS_PER_ASSIGNMENT


def test_has_reached_draft_limit_is_false_below_the_limit(monkeypatch):
    monkeypatch.setenv(MAX_DRAFTS_ENV_VAR, "3")
    assert has_reached_draft_limit(2) is False


def test_has_reached_draft_limit_is_true_at_the_limit(monkeypatch):
    monkeypatch.setenv(MAX_DRAFTS_ENV_VAR, "3")
    assert has_reached_draft_limit(3) is True


def test_has_reached_draft_limit_is_true_above_the_limit(monkeypatch):
    monkeypatch.setenv(MAX_DRAFTS_ENV_VAR, "3")
    assert has_reached_draft_limit(4) is True


def test_has_reached_draft_limit_is_false_for_a_brand_new_assignment(monkeypatch):
    monkeypatch.delenv(MAX_DRAFTS_ENV_VAR, raising=False)
    assert has_reached_draft_limit(0) is False
