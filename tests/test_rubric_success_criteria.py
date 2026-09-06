"""Tests for Stage 2: Rubric / Success Criteria Reviewer.

These tests never call a live model -- they substitute a fake chat model so
the suite runs offline and deterministically. What they verify is the wiring
(the assignment/rubric/teacher-instructions/Stage-1 text all reach the
model, missing inputs are handled without error) and that the structured
output contract holds. Whether the model actually grounds its output in the
rubric's own terminology is a property of real model reasoning, checked in
test_rubric_success_criteria_live.py instead.
"""

from pathlib import Path

import pytest

from ammu_review.assignment_understanding import AssignmentUnderstanding
from ammu_review.rubric_success_criteria import (
    SYSTEM_PROMPT_TEXT,
    RubricCriterion,
    RubricSuccessCriteria,
    review_rubric_success_criteria,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

SAMPLE_RESULT = RubricSuccessCriteria(
    rubric_provided=True,
    criteria=[
        RubricCriterion(
            code="5.3",
            name="Examines the role of law in society",
            teacher_wording="Student clearly identifies the Australian Law, the source, legal terms and concepts.",
            student_friendly_meaning="Show which law applies, where it comes from, and what its key terms mean.",
            observable_evidence=["Names the specific law and its source", "Defines legal terms used"],
            top_band_requirements=["Clearly identifies and links the summary to outcome and justification in written form."],
            good_vs_outstanding="A good response identifies the law; an outstanding one clearly links summary, outcome, and justification together.",
            common_failure_modes=["Naming the law without explaining the source", "Listing terms without linking them to the case"],
        )
    ],
    overall_top_band_profile="A top-band response clearly identifies the law and links every part of the analysis together.",
    success_checklist=["Name the law and its source", "Define every legal term used"],
    limitations=[],
)


class _FakeStructuredModel:
    """Stands in for ``model.with_structured_output(...)``."""

    def __init__(self, result: RubricSuccessCriteria):
        self.result = result
        self.received = None

    async def ainvoke(self, messages, *args, **kwargs):
        self.received = messages
        return self.result


class _FakeChatModel:
    """Stands in for the chat model itself -- captures what it was asked."""

    def __init__(self, result: RubricSuccessCriteria):
        self.structured = _FakeStructuredModel(result)

    def with_structured_output(self, schema):
        assert schema is RubricSuccessCriteria
        return self.structured


@pytest.fixture
def sample_assignment() -> str:
    return (DATA_DIR / "hannah_clarke_task.md").read_text()


@pytest.fixture
def sample_rubric() -> str:
    return (DATA_DIR / "hannah_clarke_rubric.md").read_text()


async def test_review_rubric_success_criteria_returns_structured_output(sample_assignment, sample_rubric):
    fake_model = _FakeChatModel(SAMPLE_RESULT)

    result = await review_rubric_success_criteria(
        assignment=sample_assignment,
        rubric=sample_rubric,
        model=fake_model,
    )

    assert isinstance(result, RubricSuccessCriteria)
    assert result == SAMPLE_RESULT


async def test_assignment_and_rubric_reach_the_model(sample_assignment, sample_rubric):
    fake_model = _FakeChatModel(SAMPLE_RESULT)

    await review_rubric_success_criteria(assignment=sample_assignment, rubric=sample_rubric, model=fake_model)

    human_message = fake_model.structured.received[1]
    assert sample_assignment.strip() in human_message.content
    assert sample_rubric.strip() in human_message.content


async def test_stage1_result_reaches_the_model_when_provided(sample_assignment, sample_rubric):
    fake_model = _FakeChatModel(SAMPLE_RESULT)
    understanding = AssignmentUnderstanding(
        main_task="Research and present on one area of Australian Law.",
        requirements=["Collect 5-6 articles"],
        assessed_skills=["5.3 — Examines the role of law in society."],
        command_words=["Analyse: examine the articles."],
        hidden_traps=["Missing the word count."],
        top_band_thinking=["Extensive, well-justified analysis."],
        checklist=["Choose an area of law."],
    )

    await review_rubric_success_criteria(
        assignment=sample_assignment,
        rubric=sample_rubric,
        assignment_understanding=understanding,
        model=fake_model,
    )

    human_message = fake_model.structured.received[1]
    assert "Research and present on one area of Australian Law." in human_message.content


async def test_missing_rubric_and_teacher_instructions_handled_gracefully(sample_assignment):
    fake_model = _FakeChatModel(SAMPLE_RESULT)

    result = await review_rubric_success_criteria(assignment=sample_assignment, model=fake_model)

    assert isinstance(result, RubricSuccessCriteria)
    human_message = fake_model.structured.received[1]
    assert "Not provided." in human_message.content


def test_prompt_treats_rubric_as_source_of_truth():
    assert "The supplied rubric is the source of truth" in SYSTEM_PROMPT_TEXT
    assert "Do not write the assignment" in SYSTEM_PROMPT_TEXT
    assert "Do NOT pretend to know the teacher's success criteria" in SYSTEM_PROMPT_TEXT
    assert "Do not fill the gap with generic assumptions" in SYSTEM_PROMPT_TEXT
