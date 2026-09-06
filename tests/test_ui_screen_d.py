"""Tests for Screen D ("Toughest Teacher") of the Streamlit student
experience, and Screen C's revision-entry/navigation additions.

Offline: builds a fully-populated two-draft AssignmentSession directly (no
model calls) and drives ui/app.py via Streamlit's AppTest by priming
session_state before the first run -- the same deterministic approach used
in test_ui_screen_c.py. Clicking "Challenge my work" would trigger a real
Stage 5 call (there's no offline seam for it, same constraint Screen C's
"Get my review" button has), so that specific transition is covered only by
test_ui_screen_d_live.py; what's covered here is everything Screen D does
once a challenge already exists, and that revisiting an already-challenged
draft never re-triggers one.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from ammu_review.app.models import Assignment, AssignmentSession, Draft
from ammu_review.app.store import SessionStore
from ammu_review.assignment_understanding import AssignmentUnderstanding
from ammu_review.priority_coach import CriterionRef, PriorityCoach
from ammu_review.rubric_success_criteria import RubricCriterion, RubricSuccessCriteria
from ammu_review.student_work_review import (
    AnalysisReview,
    DimensionReview,
    RubricTrajectory,
    StudentWorkReview,
)
from ammu_review.telemetry.models import EventType
from ammu_review.telemetry.store import TelemetryStore
from ammu_review.toughest_teacher import TeacherChallenge, ToughestTeacherReview

APP_PATH = Path(__file__).resolve().parents[1] / "ui" / "app.py"


@pytest.fixture(autouse=True)
def _reset_streamlit_resource_cache():
    st.cache_resource.clear()
    yield


def _dimension(status: str = "partial") -> DimensionReview:
    return DimensionReview(status=status, observation="Some observation.")


def _minimal_student_work_review(strength: str) -> StudentWorkReview:
    return StudentWorkReview(
        strengths=[strength],
        task_alignment="Addresses most requirements.",
        rubric_assessment=[],
        evidence_reviews=[],
        analysis_review=AnalysisReview(
            what=_dimension("strong"), how=_dimension("partial"), why=_dimension("missing"), so_what=_dimension("missing")
        ),
        issues=[],
        limitations=[],
    )


def _trajectory(estimated_grade) -> RubricTrajectory:
    return RubricTrajectory(
        rubric_provided=True,
        criteria=[],
        overall_estimated_score_percent=60.0,
        overall_confidence="medium",
        biggest_opportunity="Link the outcome to the wider legal system.",
        next_boundary_requirements=[],
        limitations=[],
        estimated_grade=estimated_grade,
        grade_boundaries_used=[("A", 90.0), ("B", 70.0), ("C", 50.0), ("D", 0.0)],
    )


def _priority_coach(current_grade) -> PriorityCoach:
    return PriorityCoach(
        priority_issue_id="S3-ISSUE-1",
        priority_statement="The analysis of whether justice was served lacks depth.",
        priority_category="analysis",
        why_this_matters="This is the core analytical requirement of the task.",
        primary_criterion=CriterionRef(criterion_code="5.9", criterion_name="Works independently and collaboratively"),
        also_affects_criteria=[],
        trajectory_connection="Addressing this is likely to strengthen your position.",
        student_question="What evidence could help you evaluate whether justice was served?",
        improvement_target="Justify your evaluation with evidence.",
        evidence_to_consider=[],
        other_issues_deferred=[],
        confidence="medium",
        limitations=[],
        current_grade=current_grade,
        target_grade="B",
    )


def _toughest_teacher_review(priority_status="partially_resolved") -> ToughestTeacherReview:
    return ToughestTeacherReview(
        overall_judgment="The revision names the legal concepts more clearly, but the evaluation is still thin.",
        trajectory_challenge="The current position looks optimistic given how little the outcome is evaluated.",
        priority_status=priority_status,
        priority_status_explanation="You've added more detail, but the evaluation still lacks a clear justification.",
        unresolved_issues=[
            TeacherChallenge(
                rank=1,
                issue_id="S3-ISSUE-9",
                category="analysis",
                related_criteria=[CriterionRef(criterion_code="5.9", criterion_name="Works independently")],
                observation="The evaluation states a conclusion without justifying it.",
                why_it_matters="A justified evaluation is the core analytical requirement of the task.",
                teacher_challenge="What specific evidence supports your conclusion about justice being served?",
                student_question="What specific evidence would justify your conclusion?",
            )
        ],
        resolved_or_adequately_addressed=["The legal terms are now clearly defined."],
        evidence_that_supports_judgment=["The revision includes more legal terminology."],
        what_would_change_my_mind=["A clear, evidence-based justification for the conclusion about justice."],
        final_student_question="What evidence would justify your conclusion about whether justice was served?",
        final_improvement_target="Justify your evaluation of the outcome with specific evidence from the case.",
        confidence="medium",
        limitations=[],
        current_grade="B",
        priority_coach_issue_id="S3-ISSUE-1",
    )


def _build_two_draft_session(with_challenge: bool, priority_status: str = "partially_resolved"):
    assignment = Assignment(
        title="Hannah Clarke Case Study",
        assignment_text="Explain the Hannah Clarke case and whether justice was served.",
        rubric_text="Rubric text.",
        assignment_understanding=AssignmentUnderstanding(
            main_task="Explain the case and evaluate whether justice was served.",
            requirements=[],
            assessed_skills=[],
            command_words=[],
            hidden_traps=[],
            top_band_thinking=[],
            checklist=[],
        ),
        success_criteria=RubricSuccessCriteria(
            rubric_provided=True,
            criteria=[
                RubricCriterion(
                    code="5.9",
                    name="Works independently and collaboratively",
                    teacher_wording="...",
                    student_friendly_meaning="...",
                    observable_evidence=[],
                    top_band_requirements=[],
                    good_vs_outstanding="...",
                    common_failure_modes=[],
                )
            ],
            overall_top_band_profile="...",
            success_checklist=[],
            limitations=[],
        ),
    )

    draft1 = Draft(
        assignment_id=assignment.id,
        draft_number=1,
        student_work_text="My first draft.",
        student_work_review=_minimal_student_work_review("Clear narrative of events."),
        rubric_trajectory=_trajectory("C"),
        priority_coach=_priority_coach("C"),
    )
    draft2 = Draft(
        assignment_id=assignment.id,
        draft_number=2,
        student_work_text="My revised draft.",
        student_work_review=_minimal_student_work_review("Clearly defines the relevant legal terms."),
        rubric_trajectory=_trajectory("B"),
        priority_coach=_priority_coach("B"),
    )
    if with_challenge:
        draft2.toughest_teacher_review = _toughest_teacher_review(priority_status=priority_status)
        draft2.priority_coach_checked_source_draft_id = draft1.id

    session = AssignmentSession(assignment=assignment, drafts=[draft1, draft2])
    return session, draft1, draft2


@pytest.fixture
def store():
    return SessionStore()  # picks up this test's isolated AMMU_SESSIONS_DIR from conftest.py


def _prime_screen_d(store, session, draft) -> AppTest:
    store.save(session)
    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.session_state["show_toughest_teacher"] = True
    at.run(timeout=60)
    return at


def _all_rendered_text(at: AppTest) -> str:
    parts: list[str] = []
    for kind in ("title", "header", "subheader", "markdown", "caption", "info", "warning", "success", "error"):
        for element in getattr(at, kind):
            parts.append(str(element.value))
    return "\n".join(parts)


# --- Not yet challenged: the opt-in intro ------------------------------------------


def test_screen_d_shows_opt_in_intro_when_not_yet_challenged(store):
    session, _draft1, draft2 = _build_two_draft_session(with_challenge=False)

    at = _prime_screen_d(store, session, draft2)

    assert not at.exception
    assert "Ready for the Toughest Teacher?" in [h.value for h in at.header]
    assert any("Challenge my work" == b.label for b in at.button)
    # No verdict should appear before the student has opted in.
    assert "The verdict" not in [h.value for h in at.header]


def test_screen_d_does_not_call_challenge_before_the_student_opts_in(store):
    session, _draft1, draft2 = _build_two_draft_session(with_challenge=False)

    at = _prime_screen_d(store, session, draft2)
    assert not at.exception

    telemetry_store = TelemetryStore()
    events = telemetry_store.read_events(session.assignment.id)
    assert not any(e.event_type in (EventType.PRIORITY_CHALLENGE_STARTED, EventType.PRIORITY_CHALLENGE_COMPLETED) for e in events)


# --- Already challenged: full rendering ---------------------------------------------


def test_screen_d_renders_verdict_and_hides_raw_status(store):
    session, draft1, draft2 = _build_two_draft_session(with_challenge=True, priority_status="partially_resolved")

    at = _prime_screen_d(store, session, draft2)

    assert not at.exception
    text = _all_rendered_text(at)
    assert "The verdict" in [h.value for h in at.header]
    assert "partially_resolved" not in text
    assert "You've made progress, but something still needs strengthening" in text


def test_screen_d_resolved_and_unresolved_render_distinct_wording(store):
    resolved_session, _d1, resolved_draft = _build_two_draft_session(with_challenge=True, priority_status="resolved")
    at_resolved = _prime_screen_d(SessionStore(), resolved_session, resolved_draft)
    resolved_text = _all_rendered_text(at_resolved)
    assert "You addressed the challenge" in resolved_text

    unresolved_session, _d1b, unresolved_draft = _build_two_draft_session(with_challenge=True, priority_status="unresolved")
    at_unresolved = _prime_screen_d(SessionStore(), unresolved_session, unresolved_draft)
    unresolved_text = _all_rendered_text(at_unresolved)
    assert "The main challenge is still there" in unresolved_text


def test_screen_d_shows_unresolved_issues_without_raw_ids(store):
    session, draft1, draft2 = _build_two_draft_session(with_challenge=True)

    at = _prime_screen_d(store, session, draft2)

    text = _all_rendered_text(at)
    assert "What specific evidence supports your conclusion about justice being served?" in text
    assert "S3-ISSUE" not in text
    assert "TeacherChallenge" not in text


def test_screen_d_shows_what_would_change_my_mind(store):
    session, draft1, draft2 = _build_two_draft_session(with_challenge=True)

    at = _prime_screen_d(store, session, draft2)

    text = _all_rendered_text(at)
    assert "What would change the toughest teacher's mind?" in [h.value for h in at.header]
    assert "A clear, evidence-based justification for the conclusion about justice." in text


def test_screen_d_shows_final_challenge(store):
    session, draft1, draft2 = _build_two_draft_session(with_challenge=True)

    at = _prime_screen_d(store, session, draft2)

    assert [i.value for i in at.info if i.value.startswith("What evidence would justify")]
    text = _all_rendered_text(at)
    assert "Justify your evaluation of the outcome with specific evidence from the case." in text


def test_screen_d_never_introduces_replacement_text(store):
    session, draft1, draft2 = _build_two_draft_session(with_challenge=True)

    at = _prime_screen_d(store, session, draft2)

    assert "My revised draft." not in _all_rendered_text(at)


def test_screen_d_shows_trajectory_as_an_ai_estimate_and_reflects_progress(store):
    session, draft1, draft2 = _build_two_draft_session(with_challenge=True)

    at = _prime_screen_d(store, session, draft2)

    text = _all_rendered_text(at)
    assert "Your progress" in [h.value for h in at.header]
    assert "Previous trajectory: **C**" in text or "Previous trajectory: C" in text
    assert "AI estimate" in text
    assert "not your teacher" in text.lower()
    assert "Your estimated trajectory moved." in text


def test_screen_d_handles_no_previous_priority_gracefully(store):
    session, draft1, draft2 = _build_two_draft_session(with_challenge=True, priority_status="partially_resolved")
    draft2.toughest_teacher_review = draft2.toughest_teacher_review.model_copy(
        update={"priority_status": None, "priority_status_explanation": "No priority was supplied to check."}
    )
    draft2.priority_coach_checked_source_draft_id = None

    at = _prime_screen_d(store, session, draft2)

    assert not at.exception
    info_texts = [i.value for i in at.info]
    assert any("wasn't an earlier priority to check" in text for text in info_texts)


def test_screen_d_handles_missing_previous_trajectory_gracefully(store):
    session, draft1, draft2 = _build_two_draft_session(with_challenge=True)
    draft1.rubric_trajectory = None  # simulate an old saved session missing this
    store.save(session)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft2.id
    at.session_state["show_toughest_teacher"] = True
    at.run(timeout=60)

    assert not at.exception
    # "Your progress" comparison should simply be omitted, not crash.
    assert "Your progress" not in [h.value for h in at.header]


# --- Screen C: revision entry + navigation to Screen D -------------------------------


def test_screen_c_offers_try_the_toughest_teacher(store):
    session, draft1, _draft2 = _build_two_draft_session(with_challenge=False)
    store.save(session)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft1.id
    at.run(timeout=60)

    assert not at.exception
    assert any(b.label == "Try the Toughest Teacher" for b in at.button)
    assert any(b.label == "Submit my revision" for b in at.button)


def test_clicking_try_the_toughest_teacher_navigates_to_screen_d(store):
    session, draft1, _draft2 = _build_two_draft_session(with_challenge=False)
    store.save(session)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft1.id
    at.run(timeout=60)

    button = next(b for b in at.button if b.label == "Try the Toughest Teacher")
    button.click().run(timeout=60)

    assert not at.exception
    assert at.session_state["show_toughest_teacher"] is True
    assert [t.value for t in at.title] == ["Toughest Teacher"]


def test_back_to_your_review_returns_from_screen_d_to_screen_c(store):
    session, _draft1, draft2 = _build_two_draft_session(with_challenge=True)

    at = _prime_screen_d(store, session, draft2)
    back_button = next(b for b in at.button if "Back to your review" in b.label)
    back_button.click().run(timeout=60)

    assert not at.exception
    assert at.session_state["show_toughest_teacher"] is False
    assert [t.value for t in at.title] == ["Your review"]


# --- Regression: Screens A/B/C still work -------------------------------------------


def test_screen_a_still_renders(store):
    at = AppTest.from_file(str(APP_PATH))
    at.session_state["pilot_authenticated"] = True
    at.run(timeout=60)

    assert not at.exception
    assert [t.value for t in at.title] == ["Start a new assignment"]
