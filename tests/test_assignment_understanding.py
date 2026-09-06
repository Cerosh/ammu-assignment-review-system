"""Tests for Stage 1: Assignment Understanding Reviewer.

These tests never call a live model -- they substitute a fake chat model so
the suite runs offline and deterministically. What they verify is the wiring
(the supplied assignment/rubric text actually reaches the model, missing
inputs are handled without error, the prompt's own guardrails are intact) and
that the structured output contract holds. They do not verify the semantic
quality of a real model's reasoning -- that needs a live-model eval, which is
deliberately out of scope for this stage's unit tests.
"""

from pathlib import Path

import pytest

from ammu_review.assignment_understanding import (
    SYSTEM_PROMPT_TEXT,
    AssignmentUnderstanding,
    review_assignment,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

SAMPLE_RESULT = AssignmentUnderstanding(
    main_task="Explain three causes of the Industrial Revolution and judge which "
    "consequence mattered most to ordinary people.",
    requirements=[
        "Explain at least three causes",
        "Use evidence from at least two sources",
        "Evaluate the most significant consequence and justify the judgement",
        "800-1000 words with a Chicago-style reference list",
    ],
    assessed_skills=["Knowledge & Understanding", "Use of Evidence", "Analysis", "Evaluation", "Communication"],
    command_words=["Analyse: explain relationships, not just list events", "Evaluate: make and justify a judgement"],
    hidden_traps=["Listing causes without explaining how they connect", "Giving a judgement with no justification"],
    top_band_thinking=["Explains relationships between causes and consequences rather than describing them separately"],
    checklist=["Confirm three causes are explained, not just named", "Check every claim has a linked source"],
)


class _FakeStructuredModel:
    """Stands in for ``model.with_structured_output(...)``."""

    def __init__(self, result: AssignmentUnderstanding):
        self.result = result
        self.received = None

    async def ainvoke(self, messages, *args, **kwargs):
        self.received = messages
        return self.result


class _FakeChatModel:
    """Stands in for the chat model itself -- captures what it was asked."""

    def __init__(self, result: AssignmentUnderstanding):
        self.structured = _FakeStructuredModel(result)

    def with_structured_output(self, schema):
        assert schema is AssignmentUnderstanding
        return self.structured


@pytest.fixture
def sample_assignment() -> str:
    return (DATA_DIR / "sample_assignment.md").read_text()


@pytest.fixture
def sample_rubric() -> str:
    return (DATA_DIR / "sample_rubric.md").read_text()


async def test_review_assignment_returns_structured_output(sample_assignment, sample_rubric):
    fake_model = _FakeChatModel(SAMPLE_RESULT)

    result = await review_assignment(
        assignment=sample_assignment,
        rubric=sample_rubric,
        teacher_instructions="Focus on causes, not just effects.",
        model=fake_model,
    )

    assert isinstance(result, AssignmentUnderstanding)
    assert result == SAMPLE_RESULT


async def test_assignment_text_reaches_the_model(sample_assignment):
    fake_model = _FakeChatModel(SAMPLE_RESULT)

    await review_assignment(assignment=sample_assignment, model=fake_model)

    human_message = fake_model.structured.received[1]
    assert sample_assignment.strip() in human_message.content


async def test_rubric_reaches_the_model_when_provided(sample_assignment, sample_rubric):
    fake_model = _FakeChatModel(SAMPLE_RESULT)

    await review_assignment(assignment=sample_assignment, rubric=sample_rubric, model=fake_model)

    human_message = fake_model.structured.received[1]
    assert sample_rubric.strip() in human_message.content


async def test_missing_rubric_and_teacher_instructions_handled_gracefully(sample_assignment):
    fake_model = _FakeChatModel(SAMPLE_RESULT)

    result = await review_assignment(assignment=sample_assignment, model=fake_model)

    assert isinstance(result, AssignmentUnderstanding)
    human_message = fake_model.structured.received[1]
    assert "Not provided." in human_message.content


def test_prompt_forbids_solving_the_assignment():
    assert "Do not solve the assignment" in SYSTEM_PROMPT_TEXT
    assert "Do not write any part of the assignment for her" in SYSTEM_PROMPT_TEXT
    assert "Do not invent requirements" in SYSTEM_PROMPT_TEXT
