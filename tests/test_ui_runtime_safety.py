"""Application-boundary tests for PR-3's runtime safety net: a failed
model/API call must become a safe, student-facing message (never a raw
traceback, never a leaked secret fragment), the app must stay usable
afterwards, and the draft/revision cost guard must actually block
submission before ``submit_draft`` is ever called. Offline only -- every
scenario here monkeypatches the orchestration functions the way
``ui/app.py`` imports them (``ammu_review.app.create_assignment`` etc.),
never invoking a real model.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import ammu_review.app as app_module
from ammu_review.app.models import Assignment, AssignmentSession, Draft
from ammu_review.app.store import SessionStore
from ammu_review.assignment_understanding import AssignmentUnderstanding
from ammu_review.priority_coach import CriterionRef, PriorityCoach
from ammu_review.rubric_success_criteria import RubricSuccessCriteria
from ammu_review.student_work_review import (
    AnalysisReview,
    DimensionReview,
    RubricTrajectory,
    StudentWorkReview,
)
from ammu_review.toughest_teacher import TeacherChallenge, ToughestTeacherReview

APP_PATH = Path(__file__).resolve().parents[1] / "ui" / "app.py"
ACCESS_CODE_ENV_VAR = "AMMU_PILOT_ACCESS_CODE"
MAX_DRAFTS_ENV_VAR = "AMMU_MAX_DRAFTS_PER_ASSIGNMENT"

# A fake, masked-looking API-key fragment -- stands in for what a real API
# client error message might echo back, so tests can prove it never
# reaches the student-facing error or the log.
FAKE_SECRET_FRAGMENT = "sk-should-never-leak-1234"


@pytest.fixture(autouse=True)
def _reset_streamlit_resource_cache():
    st.cache_resource.clear()
    yield


@pytest.fixture(autouse=True)
def _configured_for_access(monkeypatch):
    monkeypatch.setenv(ACCESS_CODE_ENV_VAR, "the-real-code")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-not-real")


def _minimal_understanding() -> AssignmentUnderstanding:
    return AssignmentUnderstanding(
        main_task="Explain the case and evaluate whether justice was served.",
        requirements=[],
        assessed_skills=[],
        command_words=[],
        hidden_traps=[],
        top_band_thinking=[],
        checklist=[],
    )


def _no_rubric_success_criteria() -> RubricSuccessCriteria:
    return RubricSuccessCriteria(
        rubric_provided=False,
        criteria=[],
        overall_top_band_profile="Cannot be determined without a rubric.",
        success_checklist=[],
        limitations=["No rubric was supplied."],
    )


def _dimension(status: str = "partial") -> DimensionReview:
    return DimensionReview(status=status, observation="Some observation.")


def _minimal_student_work_review() -> StudentWorkReview:
    return StudentWorkReview(
        strengths=["Clear narrative of events."],
        task_alignment="Addresses most requirements.",
        rubric_assessment=[],
        evidence_reviews=[],
        analysis_review=AnalysisReview(
            what=_dimension("strong"), how=_dimension("partial"), why=_dimension("missing"), so_what=_dimension("missing")
        ),
        issues=[],
        limitations=[],
    )


def _trajectory() -> RubricTrajectory:
    return RubricTrajectory(
        rubric_provided=False,
        criteria=[],
        overall_estimated_score_percent=None,
        overall_confidence="low",
        biggest_opportunity="Link the outcome to the wider legal system.",
        next_boundary_requirements=[],
        limitations=["No rubric was supplied."],
        estimated_grade=None,
        grade_boundaries_used=[],
    )


def _priority_coach() -> PriorityCoach:
    return PriorityCoach(
        priority_issue_id="S3-ISSUE-1",
        priority_statement="The analysis of whether justice was served lacks depth.",
        priority_category="analysis",
        why_this_matters="This is the core analytical requirement of the task.",
        primary_criterion=CriterionRef(criterion_code=None, criterion_name="Analysis"),
        also_affects_criteria=[],
        trajectory_connection="Addressing this is likely to strengthen your position.",
        student_question="What evidence could help you evaluate whether justice was served?",
        improvement_target="Justify your evaluation with evidence.",
        evidence_to_consider=[],
        other_issues_deferred=[],
        confidence="medium",
        limitations=[],
        current_grade=None,
        target_grade=None,
    )


def _toughest_teacher_review() -> ToughestTeacherReview:
    return ToughestTeacherReview(
        overall_judgment="Thin but improving.",
        trajectory_challenge="The current position looks optimistic.",
        priority_status="partially_resolved",
        priority_status_explanation="Some progress, but the evaluation still lacks justification.",
        unresolved_issues=[
            TeacherChallenge(
                rank=1,
                issue_id="S3-ISSUE-9",
                category="analysis",
                related_criteria=[],
                observation="The evaluation states a conclusion without justifying it.",
                why_it_matters="A justified evaluation is the core requirement.",
                teacher_challenge="What evidence supports your conclusion?",
                student_question="What evidence would justify your conclusion?",
            )
        ],
        resolved_or_adequately_addressed=[],
        evidence_that_supports_judgment=[],
        what_would_change_my_mind=["A clear, evidence-based justification."],
        final_student_question="What evidence would justify your conclusion?",
        final_improvement_target="Justify your evaluation with specific evidence.",
        confidence="medium",
        limitations=[],
        current_grade=None,
        priority_coach_issue_id="S3-ISSUE-1",
    )


def _new_assignment() -> Assignment:
    return Assignment(
        title="Hannah Clarke Case Study",
        assignment_text="Explain the Hannah Clarke case and whether justice was served.",
        assignment_understanding=_minimal_understanding(),
        success_criteria=_no_rubric_success_criteria(),
    )


def _reviewed_draft(assignment_id: str, draft_number: int = 1, with_challenge: bool = False) -> Draft:
    return Draft(
        assignment_id=assignment_id,
        draft_number=draft_number,
        student_work_text=f"Draft {draft_number} text.",
        student_work_review=_minimal_student_work_review(),
        rubric_trajectory=_trajectory(),
        priority_coach=_priority_coach(),
        toughest_teacher_review=_toughest_teacher_review() if with_challenge else None,
        priority_coach_checked_source_draft_id=None,
    )


# --- create_assignment failure ----------------------------------------------------


async def _raise(*args, **kwargs):
    raise RuntimeError(f"simulated failure referencing {FAKE_SECRET_FRAGMENT}")


def test_create_assignment_failure_shows_safe_error_and_stays_on_setup_screen(monkeypatch, tmp_path):
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(tmp_path / "sessions"))
    monkeypatch.setattr(app_module, "create_assignment", _raise)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.run()
    at.text_area[0].input("An assignment about the Hannah Clarke case.")
    at.run()
    at.button[0].click()
    at.run()

    assert not at.exception
    assert at.title[0].value == "Start a new assignment"
    assert "assignment_id" not in at.session_state or at.session_state["assignment_id"] is None
    assert any("Something went wrong" in e.value for e in at.error)
    assert not any(FAKE_SECRET_FRAGMENT in e.value for e in at.error)


# --- submit_draft failure, first draft --------------------------------------------


def test_submit_draft_failure_on_first_draft_stays_on_understand_screen(monkeypatch, tmp_path):
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(sessions_dir))
    store = SessionStore(base_dir=sessions_dir)
    assignment = _new_assignment()
    session = AssignmentSession(assignment=assignment, drafts=[])
    store.save(session)

    monkeypatch.setattr(app_module, "submit_draft", _raise)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.session_state["assignment_id"] = assignment.id
    at.run()
    at.text_area(key="draft_text_input").input("My first draft text.")
    at.run()
    review_button = next(b for b in at.button if b.label == "Get my review")
    review_button.click()
    at.run()

    assert not at.exception
    assert at.session_state["draft_id"] is None
    assert any("Something went wrong" in e.value for e in at.error)
    assert not any(FAKE_SECRET_FRAGMENT in e.value for e in at.error)


# --- submit_draft failure, revision -----------------------------------------------


def test_submit_draft_failure_on_revision_stays_on_review_screen(monkeypatch, tmp_path):
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(sessions_dir))
    store = SessionStore(base_dir=sessions_dir)
    assignment = _new_assignment()
    draft = _reviewed_draft(assignment.id, draft_number=1)
    session = AssignmentSession(assignment=assignment, drafts=[draft])
    store.save(session)

    monkeypatch.setattr(app_module, "submit_draft", _raise)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.session_state["assignment_id"] = assignment.id
    at.session_state["draft_id"] = draft.id
    at.run()
    at.text_area(key="revision_text_input").input("My revised draft text.")
    at.run()
    revision_button = next(b for b in at.button if b.label == "Submit my revision")
    revision_button.click()
    at.run()

    assert not at.exception
    assert at.session_state["draft_id"] == draft.id  # unchanged -- no new draft created
    assert any("Something went wrong" in e.value for e in at.error)
    assert not any(FAKE_SECRET_FRAGMENT in e.value for e in at.error)


# --- challenge_draft failure -------------------------------------------------------


def test_challenge_draft_failure_leaves_the_draft_unchallenged(monkeypatch, tmp_path):
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(sessions_dir))
    store = SessionStore(base_dir=sessions_dir)
    assignment = _new_assignment()
    draft = _reviewed_draft(assignment.id, draft_number=1, with_challenge=False)
    session = AssignmentSession(assignment=assignment, drafts=[draft])
    store.save(session)

    monkeypatch.setattr(app_module, "challenge_draft", _raise)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.session_state["assignment_id"] = assignment.id
    at.session_state["draft_id"] = draft.id
    at.session_state["show_toughest_teacher"] = True
    at.run()
    challenge_button = next(b for b in at.button if b.label == "Challenge my work")
    challenge_button.click()
    at.run()

    assert not at.exception
    assert any("Something went wrong" in e.value for e in at.error)
    assert not any(FAKE_SECRET_FRAGMENT in e.value for e in at.error)

    reloaded = store.load(assignment.id)
    assert reloaded.drafts[0].toughest_teacher_review is None


# --- rerun safety: persisted Stage 5 result is never recomputed -------------------


def test_persisted_toughest_teacher_result_is_never_recomputed(monkeypatch, tmp_path):
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(sessions_dir))
    store = SessionStore(base_dir=sessions_dir)
    assignment = _new_assignment()
    draft = _reviewed_draft(assignment.id, draft_number=1, with_challenge=True)
    session = AssignmentSession(assignment=assignment, drafts=[draft])
    store.save(session)

    async def _must_not_be_called(*args, **kwargs):
        raise AssertionError("challenge_draft must not be called when a result is already persisted")

    monkeypatch.setattr(app_module, "challenge_draft", _must_not_be_called)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.session_state["assignment_id"] = assignment.id
    at.session_state["draft_id"] = draft.id
    at.session_state["show_toughest_teacher"] = True
    at.run()

    assert not at.exception
    assert not any(b.label == "Challenge my work" for b in at.button)


# --- rerun safety: unrelated interactions never trigger a review call ------------


def test_unrelated_rerun_does_not_trigger_any_review_call(monkeypatch, tmp_path):
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(sessions_dir))
    store = SessionStore(base_dir=sessions_dir)
    assignment = _new_assignment()
    draft = _reviewed_draft(assignment.id, draft_number=1)
    session = AssignmentSession(assignment=assignment, drafts=[draft])
    store.save(session)

    async def _must_not_be_called(*args, **kwargs):
        raise AssertionError("must not be called by a plain rerun")

    monkeypatch.setattr(app_module, "create_assignment", _must_not_be_called)
    monkeypatch.setattr(app_module, "submit_draft", _must_not_be_called)
    monkeypatch.setattr(app_module, "challenge_draft", _must_not_be_called)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.session_state["assignment_id"] = assignment.id
    at.session_state["draft_id"] = draft.id
    at.run()
    # A second rerun with no button click -- simulates an unrelated widget
    # interaction (e.g. typing in the revision text area) without submitting.
    at.text_area(key="revision_text_input").input("Some text, not submitted.")
    at.run()

    assert not at.exception


# --- cost guard: draft limit blocks submission before submit_draft is called -----


def test_draft_limit_reached_blocks_revision_without_calling_submit_draft(monkeypatch, tmp_path):
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(sessions_dir))
    monkeypatch.setenv(MAX_DRAFTS_ENV_VAR, "1")
    store = SessionStore(base_dir=sessions_dir)
    assignment = _new_assignment()
    draft = _reviewed_draft(assignment.id, draft_number=1)
    session = AssignmentSession(assignment=assignment, drafts=[draft])
    store.save(session)

    async def _must_not_be_called(*args, **kwargs):
        raise AssertionError("submit_draft must not be called once the draft limit is reached")

    monkeypatch.setattr(app_module, "submit_draft", _must_not_be_called)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.session_state["assignment_id"] = assignment.id
    at.session_state["draft_id"] = draft.id
    at.run()

    assert not at.exception
    assert any("maximum number of draft submissions" in w.value for w in at.warning)
    assert not any(b.label == "Submit my revision" for b in at.button)
    assert not any(ta.key == "revision_text_input" for ta in at.text_area)


def test_draft_limit_not_yet_reached_still_allows_normal_revision(monkeypatch, tmp_path):
    sessions_dir = tmp_path / "sessions"
    monkeypatch.setenv("AMMU_SESSIONS_DIR", str(sessions_dir))
    monkeypatch.setenv(MAX_DRAFTS_ENV_VAR, "10")
    store = SessionStore(base_dir=sessions_dir)
    assignment = _new_assignment()
    draft = _reviewed_draft(assignment.id, draft_number=1)
    session = AssignmentSession(assignment=assignment, drafts=[draft])
    store.save(session)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.session_state["assignment_id"] = assignment.id
    at.session_state["draft_id"] = draft.id
    at.run()

    assert not at.exception
    assert any(b.label == "Submit my revision" for b in at.button)
    assert not any("maximum number of draft submissions" in w.value for w in at.warning)
