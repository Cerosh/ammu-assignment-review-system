"""Tests for SessionStore: JSON-file persistence of AssignmentSession.

All tests use tmp_path as the base directory -- never the real
data/sessions/ directory -- so they never touch real pilot data.
"""

from __future__ import annotations

import pytest

from ammu_review.app.models import Assignment, AssignmentSession, Draft
from ammu_review.app.store import SessionStore


def test_save_then_load_round_trips(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    assignment = Assignment(assignment_text="Write an essay.")
    session = AssignmentSession(assignment=assignment)

    store.save(session)
    loaded = store.load(assignment.id)

    assert loaded.assignment.id == assignment.id
    assert loaded.assignment.assignment_text == "Write an essay."
    assert loaded.drafts == []


def test_save_overwrites_previous_version(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    assignment = Assignment(assignment_text="Write an essay.")
    session = AssignmentSession(assignment=assignment)
    store.save(session)

    session.drafts.append(Draft(assignment_id=assignment.id, draft_number=1, student_work_text="Draft 1"))
    store.save(session)

    loaded = store.load(assignment.id)
    assert len(loaded.drafts) == 1
    assert loaded.drafts[0].student_work_text == "Draft 1"


def test_load_missing_assignment_raises(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        store.load("does-not-exist")


def test_exists(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    assignment = Assignment(assignment_text="Write an essay.")
    assert not store.exists(assignment.id)
    store.save(AssignmentSession(assignment=assignment))
    assert store.exists(assignment.id)


def test_list_assignment_ids(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    a1 = Assignment(assignment_text="Essay 1")
    a2 = Assignment(assignment_text="Essay 2")
    store.save(AssignmentSession(assignment=a1))
    store.save(AssignmentSession(assignment=a2))

    ids = store.list_assignment_ids()
    assert sorted(ids) == sorted([a1.id, a2.id])


def test_base_dir_is_created_if_missing(tmp_path):
    base_dir = tmp_path / "nested" / "sessions"
    assert not base_dir.exists()
    SessionStore(base_dir=base_dir)
    assert base_dir.exists()


def test_base_dir_defaults_from_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(tmp_path / "from_env"))
    store = SessionStore()
    assert store.base_dir == tmp_path / "from_env"
    assert store.base_dir.exists()
