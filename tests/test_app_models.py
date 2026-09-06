"""Tests for the application-layer models: Assignment, Draft, AssignmentSession.

These are plain Pydantic models with no AI calls involved -- tests just
check id/timestamp defaults and that the session round-trips through JSON
the same way SessionStore relies on.
"""

from __future__ import annotations

from ammu_review.app.models import Assignment, AssignmentSession, Draft


def test_assignment_gets_a_default_unique_id():
    a1 = Assignment(assignment_text="Write an essay.")
    a2 = Assignment(assignment_text="Write an essay.")
    assert a1.id != a2.id
    assert a1.id  # non-empty


def test_assignment_optional_fields_default_to_none():
    a = Assignment(assignment_text="Write an essay.")
    assert a.rubric_text is None
    assert a.teacher_instructions_text is None
    assert a.assignment_understanding is None
    assert a.success_criteria is None


def test_draft_gets_a_default_unique_id_and_links_to_assignment():
    d1 = Draft(assignment_id="abc123", draft_number=1, student_work_text="My draft.")
    d2 = Draft(assignment_id="abc123", draft_number=2, student_work_text="My second draft.")
    assert d1.id != d2.id
    assert d1.assignment_id == "abc123"
    assert d1.priority_coach_checked_source_draft_id is None


def test_assignment_session_round_trips_through_json():
    assignment = Assignment(assignment_text="Write an essay.", title="Hannah Clarke Case Study")
    draft = Draft(assignment_id=assignment.id, draft_number=1, student_work_text="My draft.")
    session = AssignmentSession(assignment=assignment, drafts=[draft])

    restored = AssignmentSession.model_validate_json(session.model_dump_json())

    assert restored.assignment.id == assignment.id
    assert restored.assignment.title == "Hannah Clarke Case Study"
    assert len(restored.drafts) == 1
    assert restored.drafts[0].id == draft.id
    assert restored.drafts[0].student_work_text == "My draft."


def test_assignment_session_defaults_to_no_drafts():
    session = AssignmentSession(assignment=Assignment(assignment_text="Write an essay."))
    assert session.drafts == []
