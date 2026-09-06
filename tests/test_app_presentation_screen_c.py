"""Tests for the Screen C ("Your Review") presentation translators:
present_priority, present_rubric_trajectory, present_rubric_check,
present_other_issues, present_strengths.

Pure functions, no model involved -- these check field mapping, that no
raw issue id or internal AI vocabulary leaks into the output, and that
missing/partial upstream data is handled without crashing.
"""

from __future__ import annotations

from ammu_review.app.presentation import (
    present_other_issues,
    present_priority,
    present_rubric_check,
    present_rubric_trajectory,
    present_strengths,
)
from ammu_review.priority_coach import CriterionRef, PriorityCoach
from ammu_review.student_work_review import (
    AnalysisReview,
    CriterionTrajectory,
    DimensionReview,
    ReviewIssue,
    RubricAssessment,
    RubricTrajectory,
    StudentWorkReview,
)


def _dimension(status: str = "partial") -> DimensionReview:
    return DimensionReview(status=status, observation="Some observation.")


def _priority_coach(priority_issue_id="S3-ISSUE-2") -> PriorityCoach:
    return PriorityCoach(
        priority_issue_id=priority_issue_id,
        priority_statement="The analysis of whether justice was served lacks depth.",
        priority_category="analysis",
        why_this_matters="This is the core analytical requirement of the task.",
        primary_criterion=CriterionRef(criterion_code="5.9", criterion_name="Works independently and collaboratively"),
        also_affects_criteria=[],
        trajectory_connection="Addressing this is likely to strengthen your position.",
        student_question="What evidence could help you evaluate whether justice was served?",
        improvement_target="Justify your evaluation with evidence.",
        evidence_to_consider=["The specific circumstances of how the case concluded."],
        other_issues_deferred=["S3-ISSUE-1"],
        confidence="medium",
        limitations=[],
        current_grade="C",
        target_grade="B",
    )


# --- present_priority ------------------------------------------------------------


def test_present_priority_maps_fields_without_exposing_issue_id():
    presented = present_priority(_priority_coach())

    assert presented["available"] is True
    assert presented["priority_statement"] == "The analysis of whether justice was served lacks depth."
    assert presented["why_it_matters"] == "This is the core analytical requirement of the task."
    assert presented["criterion"] == {"code": "5.9", "name": "Works independently and collaboratively"}
    assert presented["student_question"].endswith("?")
    # Never exposes the raw issue id or the internal category field.
    assert "S3-ISSUE" not in str(presented)
    assert "priority_issue_id" not in presented
    assert "priority_category" not in presented


def test_present_priority_handles_missing_priority_coach():
    presented = present_priority(None)
    assert presented == {"available": False}


# --- present_rubric_trajectory -----------------------------------------------------


def test_present_rubric_trajectory_computes_per_criterion_grade_from_existing_boundaries():
    trajectory = RubricTrajectory(
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
            CriterionTrajectory(
                criterion_code="5.8",
                criterion_name="Explains information using a variety of forms",
                estimated_score_percent=None,
                confidence="low",
                rationale="Not enough evidence in the draft to estimate this.",
                limitation="No media variety was evident in this draft.",
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

    presented = present_rubric_trajectory(trajectory)

    assert presented["available"] is True
    assert presented["overall_estimated_grade"] == "C"
    assert presented["biggest_opportunity"] == "Link the outcome to the wider legal system."
    assert presented["next_boundary_requirements"] == ["Provide a more justified evaluation of the outcome."]

    first, second = presented["criteria"]
    assert first["code"] == "5.3"
    assert first["estimated_grade"] == "C"  # 55% under (A>=90,B>=70,C>=50,D<50) -> "C", not invented
    assert second["estimated_grade"] is None  # no percent supplied -> no grade invented
    assert second["limitation"] == "No media variety was evident in this draft."


def test_present_rubric_trajectory_handles_missing_trajectory():
    presented = present_rubric_trajectory(None)
    assert presented["available"] is False
    assert "message" in presented


def test_present_rubric_trajectory_handles_no_rubric_supplied():
    trajectory = RubricTrajectory(
        rubric_provided=False,
        criteria=[],
        overall_estimated_score_percent=None,
        overall_confidence="low",
        biggest_opportunity="",
        next_boundary_requirements=[],
        limitations=["No marking rubric was supplied."],
        estimated_grade=None,
        grade_boundaries_used=[],
    )

    presented = present_rubric_trajectory(trajectory)

    assert presented["available"] is False
    assert "no marking rubric" in presented["message"].lower()


# --- present_rubric_check ----------------------------------------------------------


def test_present_rubric_check_maps_fields():
    review = StudentWorkReview(
        strengths=[],
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
        issues=[],
        limitations=[],
    )

    presented = present_rubric_check(review)

    assert presented["available"] is True
    criterion = presented["criteria"][0]
    assert criterion["code"] == "5.3"
    assert criterion["current_level"] == "sound"
    assert criterion["whats_working"] == ["Names the relevant law."]
    assert criterion["whats_missing"] == ["Link the outcome to a wider effect."]


def test_present_rubric_check_handles_no_rubric_assessment():
    review = StudentWorkReview(
        strengths=[],
        task_alignment="Addresses most requirements.",
        rubric_assessment=[],
        evidence_reviews=[],
        analysis_review=AnalysisReview(
            what=_dimension(), how=_dimension(), why=_dimension(), so_what=_dimension()
        ),
        issues=[],
        limitations=[],
    )

    assert present_rubric_check(review) == {"available": False}


def test_present_rubric_check_handles_missing_review():
    assert present_rubric_check(None) == {"available": False}


# --- present_other_issues + present_strengths ---------------------------------------


def _issue(issue_id: str, category: str = "grammar") -> ReviewIssue:
    return ReviewIssue(
        id=issue_id,
        category=category,
        severity="low",
        location="First sentence.",
        observation="A minor wording issue.",
        why_it_matters="Minor clarity impact.",
        student_question="How could you reword this for clarity?",
    )


def test_present_other_issues_excludes_the_priority_issue_and_translates_category():
    review = StudentWorkReview(
        strengths=[],
        task_alignment="Addresses most requirements.",
        rubric_assessment=[],
        evidence_reviews=[],
        analysis_review=AnalysisReview(
            what=_dimension(), how=_dimension(), why=_dimension(), so_what=_dimension()
        ),
        issues=[_issue("S3-ISSUE-1", "grammar"), _issue("S3-ISSUE-2", "evidence")],
        limitations=[],
    )

    presented = present_other_issues(review, priority_issue_id="S3-ISSUE-2")

    assert len(presented) == 1
    assert presented[0]["category"] == "Grammar and wording"
    assert "S3-ISSUE" not in str(presented)


def test_present_other_issues_handles_missing_review():
    assert present_other_issues(None, priority_issue_id=None) == []


def test_present_strengths_passes_through_specific_strengths():
    review = StudentWorkReview(
        strengths=["Clearly identifies the relevant Domestic Violence Order provisions."],
        task_alignment="Addresses most requirements.",
        rubric_assessment=[],
        evidence_reviews=[],
        analysis_review=AnalysisReview(
            what=_dimension(), how=_dimension(), why=_dimension(), so_what=_dimension()
        ),
        issues=[],
        limitations=[],
    )

    assert present_strengths(review) == ["Clearly identifies the relevant Domestic Violence Order provisions."]


def test_present_strengths_handles_missing_review():
    assert present_strengths(None) == []
