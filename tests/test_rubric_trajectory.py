"""Tests for the Rubric Trajectory capability (additive, alongside Stage 3).

These tests never call a live model -- they substitute a fake chat model so
the suite runs offline and deterministically. What they verify is the wiring
(assignment/rubric/student-work/Stage-1/Stage-2 text reach the model, missing
inputs are handled without error), the structured output contract, and --
crucially -- that grade computation from an estimated percent is pure Python
logic using configurable boundaries, never something the model is trusted to
compute itself. Whether the model's own estimates are actually grounded in
the rubric is checked in test_rubric_trajectory_live.py.
"""

from pathlib import Path

import pytest

from ammu_review.student_work_review import (
    TRAJECTORY_SYSTEM_PROMPT_TEXT,
    CriterionTrajectory,
    RubricTrajectory,
    _RubricTrajectoryDraft,
    grade_for_percent,
    review_rubric_trajectory,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

SAMPLE_DRAFT = _RubricTrajectoryDraft(
    rubric_provided=True,
    criteria=[
        CriterionTrajectory(
            criterion_code="5.3",
            criterion_name="Examines the role of law in society",
            estimated_score_percent=60.0,
            confidence="medium",
            rationale="Identifies the area of law but the summary-outcome-justification link is weak.",
            limitation=None,
        )
    ],
    overall_estimated_score_percent=60.0,
    overall_confidence="medium",
    biggest_opportunity="Linking the case summary more explicitly to the outcome and justification.",
    next_boundary_requirements=["Explain how the outcome follows from the legal concepts discussed."],
    limitations=[],
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
        assert schema is _RubricTrajectoryDraft
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


# --- grade_for_percent: pure Python logic, no model involved ---------------


def test_grade_for_percent_default_boundaries():
    assert grade_for_percent(95.0) == "A"
    assert grade_for_percent(90.0) == "A"
    assert grade_for_percent(89.9) == "B"
    assert grade_for_percent(70.0) == "B"
    assert grade_for_percent(69.9) == "C"
    assert grade_for_percent(50.0) == "C"
    assert grade_for_percent(49.9) == "D"
    assert grade_for_percent(0.0) == "D"


def test_grade_for_percent_none_when_percent_is_none():
    assert grade_for_percent(None) is None


def test_grade_for_percent_custom_boundaries_not_hardcoded():
    custom = (("Distinction", 95.0), ("Pass", 50.0), ("Fail", 0.0))
    assert grade_for_percent(96.0, custom) == "Distinction"
    assert grade_for_percent(60.0, custom) == "Pass"
    assert grade_for_percent(10.0, custom) == "Fail"
    # same percent, default boundaries, gives a different label -- proves
    # boundaries aren't baked into the logic
    assert grade_for_percent(60.0) == "C"


def test_grade_for_percent_handles_unsorted_boundaries():
    unsorted = (("D", 0.0), ("A", 90.0), ("C", 50.0), ("B", 70.0))
    assert grade_for_percent(95.0, unsorted) == "A"


# --- review_rubric_trajectory wiring ---------------------------------------


async def test_review_rubric_trajectory_returns_structured_output_with_computed_grade(
    sample_assignment, sample_rubric, sample_student_work
):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)

    result = await review_rubric_trajectory(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        model=fake_model,
    )

    assert isinstance(result, RubricTrajectory)
    assert result.overall_estimated_score_percent == 60.0
    # Grade is computed in Python from the percent, not produced by the model.
    assert result.estimated_grade == "C"
    assert result.grade_boundaries_used[0] == ("A", 90.0)


async def test_custom_grade_boundaries_change_the_computed_grade(
    sample_assignment, sample_rubric, sample_student_work
):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)
    lenient_boundaries = (("A", 55.0), ("B", 40.0), ("C", 25.0), ("D", 0.0))

    result = await review_rubric_trajectory(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        grade_boundaries=lenient_boundaries,
        model=fake_model,
    )

    # Same 60% estimate, different (caller-supplied) boundaries -> different grade.
    assert result.estimated_grade == "A"


async def test_assignment_rubric_and_student_work_reach_the_model(
    sample_assignment, sample_rubric, sample_student_work
):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)

    await review_rubric_trajectory(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        model=fake_model,
    )

    human_message = fake_model.structured.received[1]
    assert sample_assignment.strip() in human_message.content
    assert sample_rubric.strip() in human_message.content
    assert sample_student_work.strip() in human_message.content


async def test_missing_rubric_and_context_handled_gracefully(sample_assignment, sample_student_work):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)

    result = await review_rubric_trajectory(
        assignment=sample_assignment,
        student_work=sample_student_work,
        model=fake_model,
    )

    assert isinstance(result, RubricTrajectory)
    human_message = fake_model.structured.received[1]
    assert "Not provided." in human_message.content


def test_prompt_frames_this_as_an_estimate_not_a_prediction():
    assert "NOT a prediction of the teacher's actual" in TRAJECTORY_SYSTEM_PROMPT_TEXT
    assert "Never claim certainty" in TRAJECTORY_SYSTEM_PROMPT_TEXT
    assert "Do NOT compute or state a letter grade yourself" in TRAJECTORY_SYSTEM_PROMPT_TEXT
    assert "Do not write, rewrite, or supply replacement content" in TRAJECTORY_SYSTEM_PROMPT_TEXT
