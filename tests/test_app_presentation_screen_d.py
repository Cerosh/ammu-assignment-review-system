"""Tests for the Screen D ("Toughest Teacher") presentation translators:
present_toughest_teacher, present_revision_comparison.

Pure functions, no model involved -- these check field mapping, that no
raw issue id/rank or internal field name leaks into the output, and that
missing/partial upstream data is handled without crashing.
"""

from __future__ import annotations

from ammu_review.app.presentation import present_revision_comparison, present_toughest_teacher
from ammu_review.priority_coach import CriterionRef
from ammu_review.student_work_review import GradeBoundary, RubricTrajectory
from ammu_review.toughest_teacher import TeacherChallenge, ToughestTeacherReview

DEFAULT_BOUNDARIES: list[GradeBoundary] = [("A", 90.0), ("B", 70.0), ("C", 50.0), ("D", 0.0)]


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
        grade_boundaries_used=DEFAULT_BOUNDARIES,
    )


def _review(priority_status="unresolved", **overrides) -> ToughestTeacherReview:
    defaults = dict(
        overall_judgment="The work names the legal concepts but the evaluation of the outcome is underdeveloped.",
        trajectory_challenge="The current position looks optimistic given how little the outcome is evaluated.",
        priority_status=priority_status,
        priority_status_explanation="The evaluation of the outcome still lacks depth.",
        unresolved_issues=[
            TeacherChallenge(
                rank=1,
                issue_id="S3-ISSUE-2",
                category="analysis",
                related_criteria=[CriterionRef(criterion_code="5.9", criterion_name="Works independently")],
                observation="Ammu states an outcome but doesn't analyse its implications.",
                why_it_matters="This is the core analytical requirement of the task.",
                teacher_challenge="What does the outcome actually tell us about the legal system's effectiveness?",
                student_question="What are the consequences when a perpetrator dies before facing justice?",
            )
        ],
        resolved_or_adequately_addressed=["The DVO history is now clearly explained."],
        evidence_that_supports_judgment=["The work names the relevant legal concepts."],
        what_would_change_my_mind=["A clearer justified evaluation of the outcome, tied to evidence."],
        final_student_question="What are the consequences when a perpetrator dies before facing justice?",
        final_improvement_target="Justify your evaluation of the outcome with evidence.",
        confidence="medium",
        limitations=[],
        current_grade="C",
        priority_coach_issue_id="S3-ISSUE-2",
    )
    defaults.update(overrides)
    return ToughestTeacherReview(**defaults)


# --- present_toughest_teacher --------------------------------------------------------


def test_present_toughest_teacher_maps_verdict_and_hides_raw_status():
    presented = present_toughest_teacher(_review(priority_status="unresolved"))

    assert presented["available"] is True
    assert presented["had_previous_priority_to_check"] is True
    assert presented["verdict"] == "The main challenge is still there"
    assert "unresolved" not in presented["verdict"].lower()
    assert presented["priority_status_explanation"] == "The evaluation of the outcome still lacks depth."


def test_present_toughest_teacher_resolved_and_partially_resolved_have_distinct_wording():
    resolved = present_toughest_teacher(_review(priority_status="resolved"))
    partial = present_toughest_teacher(_review(priority_status="partially_resolved"))

    assert resolved["verdict"] == "You addressed the challenge"
    assert partial["verdict"] == "You've made progress, but something still needs strengthening"
    assert resolved["verdict"] != partial["verdict"]


def test_present_toughest_teacher_no_previous_priority_is_explained_not_invented():
    presented = present_toughest_teacher(_review(priority_status=None))

    assert presented["had_previous_priority_to_check"] is False
    assert presented["verdict"] is None


def test_present_toughest_teacher_hides_issue_id_rank_and_raw_category():
    presented = present_toughest_teacher(_review())

    serialized = str(presented)
    assert "S3-ISSUE" not in serialized
    assert "rank" not in presented["unresolved_issues"][0]
    assert "issue_id" not in presented["unresolved_issues"][0]
    assert presented["unresolved_issues"][0]["category"] == "Your thinking and analysis"


def test_present_toughest_teacher_exposes_tier_3_and_tier_4_fields():
    presented = present_toughest_teacher(_review())

    assert presented["what_would_change_my_mind"] == [
        "A clearer justified evaluation of the outcome, tied to evidence."
    ]
    assert presented["final_student_question"].endswith("?")
    assert presented["final_improvement_target"] == "Justify your evaluation of the outcome with evidence."
    assert presented["current_grade"] == "C"


def test_present_toughest_teacher_handles_missing_review():
    assert present_toughest_teacher(None) == {"available": False}


# --- present_revision_comparison -----------------------------------------------------


def test_present_revision_comparison_detects_a_change():
    presented = present_revision_comparison(_trajectory("B"), _trajectory("C"))

    assert presented["available"] is True
    assert presented["previous_grade"] == "C"
    assert presented["current_grade"] == "B"
    assert presented["trajectory_changed"] is True


def test_present_revision_comparison_detects_no_change():
    presented = present_revision_comparison(_trajectory("C"), _trajectory("C"))

    assert presented["trajectory_changed"] is False


def test_present_revision_comparison_unavailable_without_both_trajectories():
    assert present_revision_comparison(None, _trajectory("C")) == {"available": False}
    assert present_revision_comparison(_trajectory("C"), None) == {"available": False}
    assert present_revision_comparison(None, None) == {"available": False}


def test_present_revision_comparison_does_not_invent_a_change_when_grade_unknown():
    presented = present_revision_comparison(_trajectory(None), _trajectory("C"))

    assert presented["available"] is True
    assert presented["current_grade"] is None
    assert presented["trajectory_changed"] is None
