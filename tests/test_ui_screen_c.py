"""Tests for Screen C ("Your Review") of the Streamlit student experience.

Offline: builds a fully-populated AssignmentSession/Draft directly (no
model calls) and drives ui/app.py via Streamlit's AppTest by priming
session_state before the first run -- a deterministic way to test Screen
C's rendering logic without paying for or depending on a real review.
test_ui_screen_c_live.py separately validates the full real end-to-end
flow (submit -> review -> Screen C) against Ammu's actual Hannah Clarke
draft.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from ammu_review.app.models import Assignment, AssignmentSession, Draft
from ammu_review.app.store import SessionStore
from ammu_review.assignment_understanding import AssignmentUnderstanding
from ammu_review.priority_coach import CriterionRef, PriorityCoach
from ammu_review.rubric_success_criteria import RubricCriterion, RubricSuccessCriteria
from ammu_review.student_work_review import (
    AnalysisReview,
    CriterionTrajectory,
    DimensionReview,
    ReviewIssue,
    RubricAssessment,
    RubricTrajectory,
    StudentWorkReview,
)
from ammu_review.telemetry.models import EventType
from ammu_review.telemetry.store import TelemetryStore

APP_PATH = Path(__file__).resolve().parents[1] / "ui" / "app.py"

DRAFT_TEXT_MARKER = "UNIQUE-STUDENT-DRAFT-MARKER-98765"


@pytest.fixture(autouse=True)
def _reset_streamlit_resource_cache():
    """ui/app.py's get_store() is wrapped in @st.cache_resource, cached for
    the life of the process -- without clearing it, a later test's AppTest
    run would reuse an earlier test's cached SessionStore (pointing at a
    different tmp_path), rather than picking up this test's own isolated
    AMMU_SESSIONS_DIR. This resets Streamlit's cache only, never ui/app.py
    itself."""
    import streamlit as st

    st.cache_resource.clear()
    yield


def _dimension(status: str = "partial") -> DimensionReview:
    return DimensionReview(status=status, observation="Some observation.")


def _build_session_with_reviewed_draft() -> tuple[AssignmentSession, Draft]:
    assignment = Assignment(
        title="Hannah Clarke Case Study",
        assignment_text="Explain the Hannah Clarke case and whether justice was served.",
        rubric_text="Rubric text.",
        assignment_understanding=AssignmentUnderstanding(
            main_task="Explain the case and evaluate whether justice was served.",
            requirements=["Summarise the case"],
            assessed_skills=["5.3 Examines the role of law in society"],
            command_words=["Discuss"],
            hidden_traps=[],
            top_band_thinking=[],
            checklist=[],
        ),
        success_criteria=RubricSuccessCriteria(
            rubric_provided=True,
            criteria=[
                RubricCriterion(
                    code="5.3",
                    name="Examines the role of law in society",
                    teacher_wording="Analyses how the law responds to social issues.",
                    student_friendly_meaning="Show how the law reacted to this situation.",
                    observable_evidence=[],
                    top_band_requirements=[],
                    good_vs_outstanding="Outstanding responses justify the link with evidence.",
                    common_failure_modes=[],
                )
            ],
            overall_top_band_profile="Links the case to the broader legal system.",
            success_checklist=[],
            limitations=[],
        ),
    )

    student_work_review = StudentWorkReview(
        strengths=["Clearly identifies the relevant Domestic Violence Order provisions."],
        task_alignment="Addresses most requirements.",
        rubric_assessment=[
            RubricAssessment(
                criterion_code="5.3",
                criterion_name="Examines the role of law in society",
                current_level="sound",
                confidence="medium",
                evidence=["Names the relevant law."],
                gap_to_next_level=["Link the outcome to a wider effect."],
            )
        ],
        evidence_reviews=[],
        analysis_review=AnalysisReview(
            what=_dimension("strong"), how=_dimension("partial"), why=_dimension("missing"), so_what=_dimension("missing")
        ),
        issues=[
            ReviewIssue(
                id="S3-ISSUE-1",
                category="analysis",
                severity="high",
                location="Final paragraph.",
                observation="The analysis of the outcome lacks depth.",
                why_it_matters="This is the core analytical requirement of the task.",
                student_question="What does the outcome suggest about the effectiveness of the law?",
            ),
            ReviewIssue(
                id="S3-ISSUE-2",
                category="grammar",
                severity="low",
                location="First sentence.",
                observation="A minor wording issue in the opening sentence.",
                why_it_matters="Minor clarity impact.",
                student_question="How could you reword this for clarity?",
            ),
        ],
        limitations=[],
    )

    rubric_trajectory = RubricTrajectory(
        rubric_provided=True,
        criteria=[
            CriterionTrajectory(
                criterion_code="5.3",
                criterion_name="Examines the role of law in society",
                estimated_score_percent=55.0,
                confidence="medium",
                rationale="Identifies the law but the analysis is shallow.",
                limitation=None,
            ),
        ],
        overall_estimated_score_percent=55.0,
        overall_confidence="medium",
        biggest_opportunity="Link the outcome to the wider legal system.",
        next_boundary_requirements=["Provide a more justified evaluation of the outcome."],
        limitations=[],
        estimated_grade="C",
        grade_boundaries_used=[("A", 90.0), ("B", 70.0), ("C", 50.0), ("D", 0.0)],
    )

    priority_coach = PriorityCoach(
        priority_issue_id="S3-ISSUE-1",
        priority_statement="The analysis of whether justice was served lacks depth.",
        priority_category="analysis",
        why_this_matters="This is the core analytical requirement of the task.",
        primary_criterion=CriterionRef(criterion_code="5.3", criterion_name="Examines the role of law in society"),
        also_affects_criteria=[],
        trajectory_connection="Addressing this is likely to strengthen your position.",
        student_question="What evidence could help you evaluate whether justice was served?",
        improvement_target="Justify your evaluation with evidence.",
        evidence_to_consider=[],
        other_issues_deferred=["S3-ISSUE-2"],
        confidence="medium",
        limitations=[],
        current_grade="C",
        target_grade="B",
    )

    draft = Draft(
        assignment_id=assignment.id,
        draft_number=1,
        student_work_text=f"{DRAFT_TEXT_MARKER} rest of my draft.",
        student_work_review=student_work_review,
        rubric_trajectory=rubric_trajectory,
        priority_coach=priority_coach,
    )

    session = AssignmentSession(assignment=assignment, drafts=[draft])
    return session, draft


@pytest.fixture
def populated_store():
    # tests/conftest.py's autouse fixture already points AMMU_SESSIONS_DIR
    # at this test's own tmp_path -- reuse the same default store so
    # ui/app.py's get_store() (SessionStore() with no explicit base_dir)
    # finds exactly what we just saved.
    store = SessionStore()
    session, draft = _build_session_with_reviewed_draft()
    store.save(session)
    return store, session, draft


def _all_rendered_text(at: AppTest) -> str:
    parts: list[str] = []
    for kind in ("title", "header", "subheader", "markdown", "caption", "info", "warning", "error"):
        for element in getattr(at, kind):
            parts.append(str(element.value))
    return "\n".join(parts)


def test_screen_c_renders_priority_prominently(populated_store):
    store, session, draft = populated_store

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.run(timeout=60)

    assert not at.exception
    assert [h.value for h in at.title] == ["Your review"]
    assert "🎯 Your biggest opportunity" in [h.value for h in at.header]

    text = _all_rendered_text(at)
    assert "The analysis of whether justice was served lacks depth." in text
    assert "This is the core analytical requirement of the task." in text
    assert "What evidence could help you evaluate whether justice was served?" in text


def test_screen_c_never_displays_a_raw_issue_id(populated_store):
    store, session, draft = populated_store

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.run(timeout=60)

    assert "S3-ISSUE" not in _all_rendered_text(at)


def test_screen_c_never_introduces_replacement_text(populated_store):
    """The student's own draft text (or any paraphrase of it) must never be
    echoed back as a suggested rewrite -- Screen C only shows coaching
    language derived from the review, never the draft itself."""
    store, session, draft = populated_store

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.run(timeout=60)

    assert DRAFT_TEXT_MARKER not in _all_rendered_text(at)


def test_screen_c_student_question_is_a_genuine_question(populated_store):
    store, session, draft = populated_store

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.run(timeout=60)

    assert [i.value for i in at.info] == ["What evidence could help you evaluate whether justice was served?"]


def test_screen_c_shows_rubric_trajectory_with_estimate_labelled(populated_store):
    store, session, draft = populated_store

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.run(timeout=60)

    text = _all_rendered_text(at)
    assert "Your current trajectory: C" in text
    assert "AI estimate" in text
    assert "teacher's grade" in text.lower() or "not your teacher" in text.lower()


def test_screen_c_shows_strengths(populated_store):
    store, session, draft = populated_store

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.run(timeout=60)

    text = _all_rendered_text(at)
    assert "Clearly identifies the relevant Domestic Violence Order provisions." in text


def test_screen_c_other_issues_are_collapsed_and_exclude_the_priority(populated_store):
    store, session, draft = populated_store

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.run(timeout=60)

    expander_labels = [e.label for e in at.expander]
    other_things = [label for label in expander_labels if label.startswith("Other things I noticed")]
    assert other_things == ["Other things I noticed (1)"]  # only the non-priority issue

    # The priority's own observation should not reappear inside "other issues".
    other_expander = next(e for e in at.expander if e.label.startswith("Other things I noticed"))
    other_text = "\n".join(str(m.value) for m in other_expander.markdown)
    assert "The analysis of the outcome lacks depth." not in other_text
    assert "A minor wording issue in the opening sentence." in other_text


def test_screen_c_handles_missing_rubric_gracefully(populated_store):
    store, session, draft = populated_store
    # Simulate no rubric having been supplied at all.
    draft.rubric_trajectory.rubric_provided = False
    draft.rubric_trajectory.criteria = []
    draft.rubric_trajectory.estimated_grade = None
    store.save(session)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.run(timeout=60)

    assert not at.exception
    warning_texts = [w.value for w in at.warning]
    assert any("no marking rubric was supplied" in text.lower() for text in warning_texts)


def test_screen_c_handles_missing_priority_gracefully(populated_store):
    store, session, draft = populated_store
    draft.priority_coach = None
    store.save(session)

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.run(timeout=60)

    assert not at.exception
    info_texts = [i.value for i in at.info]
    assert any("couldn't identify a clear priority" in text for text in info_texts)


def test_screen_c_emits_priority_viewed_once_and_deduplicates_on_rerun(populated_store):
    store, session, draft = populated_store

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.run(timeout=60)
    assert not at.exception

    telemetry_store = TelemetryStore()  # picks up the same isolated AMMU_TELEMETRY_DIR as the app
    events = telemetry_store.read_events(session.assignment.id)
    priority_viewed_events = [e for e in events if e.event_type == EventType.PRIORITY_VIEWED]
    assert len(priority_viewed_events) == 1
    assert priority_viewed_events[0].draft_id == draft.id
    assert priority_viewed_events[0].metadata == {"priority_issue_id": "S3-ISSUE-1", "priority_category": "analysis"}

    # A second rerun of the same script (e.g. the student scrolling, another
    # widget interaction) must not emit a second PRIORITY_VIEWED event.
    at.run(timeout=60)
    events_after_rerun = telemetry_store.read_events(session.assignment.id)
    assert len([e for e in events_after_rerun if e.event_type == EventType.PRIORITY_VIEWED]) == 1


def test_screen_c_telemetry_failure_does_not_break_the_screen(populated_store, monkeypatch, tmp_path):
    store, session, draft = populated_store
    telemetry_dir = tmp_path / "broken_telemetry"
    telemetry_dir.mkdir()
    # Pre-create a directory at the exact path the event file would be
    # written to, so TelemetryStore.append()'s open(path, "a") fails with a
    # realistic storage error (IsADirectoryError) -- the same failure shape
    # test_app_orchestration_telemetry.py's _BrokenStore exercises, just
    # produced a different way since Screen C has no seam to inject a fake
    # recorder through.
    (telemetry_dir / f"{session.assignment.id}.jsonl").mkdir()
    monkeypatch.setenv("AMMU_TELEMETRY_DIR", str(telemetry_dir))

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.run(timeout=60)

    assert not at.exception
    assert "🎯 Your biggest opportunity" in [h.value for h in at.header]


def test_back_to_assignment_overview_returns_to_screen_b(populated_store):
    store, session, draft = populated_store

    at = AppTest.from_file(str(APP_PATH))
    at.session_state["assignment_id"] = session.assignment.id
    at.session_state["draft_id"] = draft.id
    at.run(timeout=60)

    back_button = next(b for b in at.button if "Back to assignment overview" in b.label)
    back_button.click().run(timeout=60)

    assert not at.exception
    assert at.session_state["draft_id"] is None
    assert "Understand this assignment" in [t.value for t in at.title] or [t.value for t in at.title] == [
        "Hannah Clarke Case Study"
    ]
