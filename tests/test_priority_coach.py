"""Tests for Stage 4: Priority Coach.

These tests never call a live model -- they substitute a fake chat model so
the suite runs offline and deterministically. What they verify is the wiring
(all source material and AI-generated context reach the model), the
structured output contract, and -- crucially -- the Python-side safety net
that a real model needs but a fake one lets us test precisely:

- current_grade/target_grade come from Python (grade_for_percent/
  next_grade_up), never from the model.
- a hallucinated/mismatched priority_issue_id is caught and discarded.
- priority_category is overwritten from the real Stage 3 issue when the id
  is valid.

Whether the model's own priority *selection* is actually sound (foundational
over grammar, etc.) is checked in test_priority_coach_live.py.
"""

from pathlib import Path

import pytest

from ammu_review.assignment_understanding import AssignmentUnderstanding
from ammu_review.priority_coach import (
    SYSTEM_PROMPT_TEXT,
    CriterionRef,
    PriorityCoach,
    _PriorityCoachDraft,
    next_grade_up,
    review_priority_coach,
)
from ammu_review.rubric_success_criteria import RubricCriterion, RubricSuccessCriteria
from ammu_review.student_work_review import (
    AnalysisReview,
    DimensionReview,
    ReviewIssue,
    RubricTrajectory,
    StudentWorkReview,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _dimension(status: str = "partial") -> DimensionReview:
    return DimensionReview(status=status, observation="Some observation.")


SAMPLE_DRAFT = _PriorityCoachDraft(
    priority_issue_id="S3-ISSUE-2",
    priority_statement="The analysis of whether justice was served lacks depth.",
    priority_category="analysis",  # deliberately wrong -- should be overwritten from the real issue
    why_this_matters="This is the core analytical requirement of the task.",
    primary_criterion=CriterionRef(criterion_code="5.9", criterion_name="Works independently and collaboratively"),
    also_affects_criteria=[],
    trajectory_connection="Addressing this is likely to strengthen your position toward the next range.",
    student_question="What evidence from the case could help you evaluate whether justice was served?",
    improvement_target="Your analysis should move beyond stating an outcome and justify it with evidence.",
    evidence_to_consider=["The specific circumstances of how the case concluded."],
    other_issues_deferred=["S3-ISSUE-1"],
    confidence="medium",
    limitations=[],
)

SAMPLE_ISSUES = [
    ReviewIssue(
        id="S3-ISSUE-1",
        category="grammar",
        severity="low",
        location="First sentence.",
        observation="A minor wording issue.",
        why_it_matters="Minor clarity impact.",
        student_question="How could you reword this for clarity?",
    ),
    ReviewIssue(
        id="S3-ISSUE-2",
        category="rubric",
        severity="high",
        location="Final paragraph.",
        observation="The justice analysis lacks depth.",
        why_it_matters="This is a core rubric requirement.",
        student_question="What criteria could you use to judge whether justice was served?",
    ),
]

SAMPLE_STUDENT_WORK_REVIEW = StudentWorkReview(
    strengths=["Clear narrative of events."],
    task_alignment="Addresses most requirements.",
    rubric_assessment=[],
    evidence_reviews=[],
    analysis_review=AnalysisReview(
        what=_dimension("strong"), how=_dimension("partial"), why=_dimension("missing"), so_what=_dimension("missing")
    ),
    issues=SAMPLE_ISSUES,
    limitations=[],
)

SAMPLE_TRAJECTORY = RubricTrajectory(
    rubric_provided=True,
    criteria=[],
    overall_estimated_score_percent=55.0,
    overall_confidence="medium",
    biggest_opportunity="Link the case outcome more explicitly to the legal concepts discussed.",
    next_boundary_requirements=["Provide a more justified evaluation of the outcome."],
    limitations=[],
    estimated_grade="C",
    grade_boundaries_used=[("A", 90.0), ("B", 70.0), ("C", 50.0), ("D", 0.0)],
)


class _FakeStructuredModel:
    def __init__(self, result):
        self.result = result
        self.received = None

    async def ainvoke(self, messages, *args, **kwargs):
        self.received = messages
        return self.result.model_copy(deep=True)


class _FakeChatModel:
    def __init__(self, result):
        self.structured = _FakeStructuredModel(result)

    def with_structured_output(self, schema):
        assert schema is _PriorityCoachDraft
        return self.structured


@pytest.fixture
def sample_assignment() -> str:
    return (DATA_DIR / "hannah_clarke_task.md").read_text()


@pytest.fixture
def sample_rubric() -> str:
    return (DATA_DIR / "hannah_clarke_rubric.md").read_text()


@pytest.fixture
def sample_student_work() -> str:
    return (DATA_DIR / "hannah_clarke_student_work.md").read_text()


# --- next_grade_up: pure Python logic, no model involved -------------------


def test_next_grade_up_moves_one_boundary_up():
    boundaries = [("A", 90.0), ("B", 70.0), ("C", 50.0), ("D", 0.0)]
    assert next_grade_up("B", boundaries) == "A"
    assert next_grade_up("D", boundaries) == "C"
    assert next_grade_up("C", boundaries) == "B"


def test_next_grade_up_top_boundary_returns_itself():
    boundaries = [("A", 90.0), ("B", 70.0), ("C", 50.0), ("D", 0.0)]
    assert next_grade_up("A", boundaries) == "A"


def test_next_grade_up_none_cases():
    boundaries = [("A", 90.0), ("B", 70.0)]
    assert next_grade_up(None, boundaries) is None
    assert next_grade_up("A", []) is None
    assert next_grade_up("Z", boundaries) is None  # not in the boundary set


def test_next_grade_up_custom_boundaries_not_hardcoded():
    custom = [("Distinction", 95.0), ("Pass", 50.0), ("Fail", 0.0)]
    assert next_grade_up("Pass", custom) == "Distinction"
    assert next_grade_up("Fail", custom) == "Pass"


# --- review_priority_coach wiring and Python safety net --------------------


async def test_returns_structured_output_with_computed_grades(sample_assignment, sample_rubric, sample_student_work):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)

    result = await review_priority_coach(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        rubric_trajectory=SAMPLE_TRAJECTORY,
        model=fake_model,
    )

    assert isinstance(result, PriorityCoach)
    # Grades come from Python (RubricTrajectory.estimated_grade + next_grade_up), not the model.
    assert result.current_grade == "C"
    assert result.target_grade == "B"


async def test_valid_issue_id_overrides_category_from_real_stage3_issue(
    sample_assignment, sample_rubric, sample_student_work
):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)

    result = await review_priority_coach(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        model=fake_model,
    )

    assert result.priority_issue_id == "S3-ISSUE-2"
    # SAMPLE_DRAFT said "analysis" but the real S3-ISSUE-2 is "rubric" -- Python must win.
    assert result.priority_category == "rubric"
    assert not result.limitations


async def test_invalid_issue_id_is_discarded_and_logged(sample_assignment, sample_rubric, sample_student_work):
    bad_draft = SAMPLE_DRAFT.model_copy(update={"priority_issue_id": "S3-ISSUE-999"})
    fake_model = _FakeChatModel(bad_draft)

    result = await review_priority_coach(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        model=fake_model,
    )

    assert result.priority_issue_id is None
    assert any("S3-ISSUE-999" in limitation for limitation in result.limitations)
    # No real issue to defer to -- the model's own (unvalidated) category is kept.
    assert result.priority_category == "analysis"


async def test_no_student_work_review_forces_priority_issue_id_none(
    sample_assignment, sample_rubric, sample_student_work
):
    """Even if a fake/misbehaving model returns an id, there's nothing to
    validate it against when no Stage 3 review was supplied at all."""
    fake_model = _FakeChatModel(SAMPLE_DRAFT)  # SAMPLE_DRAFT has priority_issue_id set

    result = await review_priority_coach(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=None,
        model=fake_model,
    )

    assert result.priority_issue_id is None
    assert any("S3-ISSUE-2" in limitation for limitation in result.limitations)


async def test_no_rubric_trajectory_leaves_grades_none(sample_assignment, sample_rubric, sample_student_work):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)

    result = await review_priority_coach(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        rubric_trajectory=None,
        model=fake_model,
    )

    assert result.current_grade is None
    assert result.target_grade is None
    human_message = fake_model.structured.received[1]
    assert "Not available -- no Rubric Trajectory context was supplied." in human_message.content


async def test_all_context_reaches_the_model(sample_assignment, sample_rubric, sample_student_work):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)
    understanding = AssignmentUnderstanding(
        main_task="Research and present on one area of Australian Law.",
        requirements=["Collect 5-6 articles"],
        assessed_skills=["5.3 — Examines the role of law in society."],
        command_words=["Analyse: examine the articles."],
        hidden_traps=["Missing the word count."],
        top_band_thinking=["Extensive, well-justified analysis."],
        checklist=["Choose an area of law."],
    )
    success_criteria = RubricSuccessCriteria(
        rubric_provided=True,
        criteria=[
            RubricCriterion(
                code="5.3",
                name="Examines the role of law in society",
                teacher_wording="Student clearly identifies the Australian Law.",
                student_friendly_meaning="Show which law applies.",
                observable_evidence=["Names the specific law."],
                top_band_requirements=["Clearly identifies and links the summary to outcome."],
                good_vs_outstanding="Outstanding responses link everything together.",
                common_failure_modes=["Naming the law without explaining the source."],
            )
        ],
        overall_top_band_profile="Links everything together clearly.",
        success_checklist=["Does my work clearly identify the area of law, per 5.3?"],
        limitations=[],
    )

    await review_priority_coach(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        assignment_understanding=understanding,
        success_criteria=success_criteria,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        rubric_trajectory=SAMPLE_TRAJECTORY,
        model=fake_model,
    )

    human_message = fake_model.structured.received[1]
    assert sample_assignment.strip() in human_message.content
    assert sample_rubric.strip() in human_message.content
    assert sample_student_work.strip() in human_message.content
    assert "Research and present on one area of Australian Law." in human_message.content
    assert "Student clearly identifies the Australian Law." in human_message.content
    assert "justice analysis lacks depth" in human_message.content  # from SAMPLE_STUDENT_WORK_REVIEW
    assert "Link the case outcome more explicitly" in human_message.content  # from SAMPLE_TRAJECTORY
    assert "Current estimated position: C" in human_message.content
    assert "Next grade boundary to aim for: B" in human_message.content


def test_prompt_guardrails_are_present():
    assert "Ammu owns the work. The system owns the challenge." in SYSTEM_PROMPT_TEXT
    assert "Do not write, rewrite, or supply replacement content" in SYSTEM_PROMPT_TEXT
    assert "NOT contain or imply the answer" in SYSTEM_PROMPT_TEXT
    assert "never a specific point or percentage increase" not in SYSTEM_PROMPT_TEXT  # sanity: no stray wording bug
    assert "NEVER claim a specific point or percentage increase" in SYSTEM_PROMPT_TEXT
