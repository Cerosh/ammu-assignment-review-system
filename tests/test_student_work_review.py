"""Tests for Stage 3: Student Work Review.

These tests never call a live model -- they substitute a fake chat model so
the suite runs offline and deterministically. What they verify is the wiring
(assignment/rubric/student-work/Stage-1/Stage-2 text all reach the model,
missing inputs are handled without error) and that the structured output
contract holds, including the id-assignment post-processing done in Python
rather than by the model. Whether the model actually grounds its review in
the supplied material is checked in test_student_work_review_live.py.
"""

from pathlib import Path

import pytest

from ammu_review.assignment_understanding import AssignmentUnderstanding
from ammu_review.rubric_success_criteria import RubricCriterion, RubricSuccessCriteria
from ammu_review.student_work_review import (
    SYSTEM_PROMPT_TEXT,
    AnalysisReview,
    DimensionReview,
    EvidenceReview,
    ReviewIssue,
    RubricAssessment,
    StudentWorkReview,
    review_student_work,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _dimension(status: str = "partial") -> DimensionReview:
    return DimensionReview(status=status, observation="Some observation.")


SAMPLE_RESULT = StudentWorkReview(
    strengths=["Clearly names three causes of the Industrial Revolution."],
    task_alignment="Addresses causes and consequences, but the word count looks short.",
    rubric_assessment=[
        RubricAssessment(
            criterion_code="5.3",
            criterion_name="Examines the role of law in society",
            current_level="Sound",
            confidence="medium",
            evidence=["Names the area of law."],
            gap_to_next_level=["Link the summary to the outcome more explicitly."],
        )
    ],
    evidence_reviews=[
        EvidenceReview(
            claim="The social consequence was the biggest for ordinary people.",
            evidence="None found in her work.",
            relationship="unsupported",
            explanation="No evidence is cited for this judgement.",
            suggested_thinking="What in the text would support ranking this consequence as the biggest?",
        )
    ],
    analysis_review=AnalysisReview(
        what=_dimension("strong"),
        how=_dimension("partial"),
        why=_dimension("missing"),
        so_what=_dimension("missing"),
    ),
    issues=[
        ReviewIssue(
            category="evidence",
            severity="medium",
            location="Third paragraph, 'I think the social consequence was the biggest...'",
            observation="A judgement is made without citing supporting evidence.",
            why_it_matters="The rubric requires justifying the argument with reasons.",
            student_question="What evidence from your research would support this ranking?",
        )
    ],
    limitations=[],
)


class _FakeStructuredModel:
    """Stands in for ``model.with_structured_output(...)``."""

    def __init__(self, result: StudentWorkReview):
        self.result = result
        self.received = None

    async def ainvoke(self, messages, *args, **kwargs):
        self.received = messages
        return self.result.model_copy(deep=True)


class _FakeChatModel:
    """Stands in for the chat model itself -- captures what it was asked."""

    def __init__(self, result: StudentWorkReview):
        self.structured = _FakeStructuredModel(result)

    def with_structured_output(self, schema):
        assert schema is StudentWorkReview
        return self.structured


@pytest.fixture
def sample_assignment() -> str:
    return (DATA_DIR / "sample_assignment.md").read_text()


@pytest.fixture
def sample_rubric() -> str:
    return (DATA_DIR / "sample_rubric.md").read_text()


@pytest.fixture
def sample_student_work() -> str:
    return (DATA_DIR / "sample_student_work.md").read_text()


async def test_review_student_work_returns_structured_output(sample_assignment, sample_rubric, sample_student_work):
    fake_model = _FakeChatModel(SAMPLE_RESULT)

    result = await review_student_work(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        model=fake_model,
    )

    assert isinstance(result, StudentWorkReview)
    assert result.strengths == SAMPLE_RESULT.strengths


async def test_issue_ids_are_assigned_deterministically_not_by_the_model(
    sample_assignment, sample_rubric, sample_student_work
):
    fake_model = _FakeChatModel(SAMPLE_RESULT)

    result = await review_student_work(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        model=fake_model,
    )

    assert [issue.id for issue in result.issues] == ["S3-ISSUE-1"]


async def test_assignment_rubric_and_student_work_reach_the_model(
    sample_assignment, sample_rubric, sample_student_work
):
    fake_model = _FakeChatModel(SAMPLE_RESULT)

    await review_student_work(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        model=fake_model,
    )

    human_message = fake_model.structured.received[1]
    assert sample_assignment.strip() in human_message.content
    assert sample_rubric.strip() in human_message.content
    assert sample_student_work.strip() in human_message.content


async def test_stage1_and_stage2_results_reach_the_model_when_provided(
    sample_assignment, sample_rubric, sample_student_work
):
    fake_model = _FakeChatModel(SAMPLE_RESULT)
    understanding = AssignmentUnderstanding(
        main_task="Explain causes and evaluate consequences of the Industrial Revolution.",
        requirements=["Explain three causes"],
        assessed_skills=["Knowledge & Understanding"],
        command_words=["Analyse: explain relationships."],
        hidden_traps=["Describing instead of analysing."],
        top_band_thinking=["Deep understanding of causes and consequences."],
        checklist=["Confirm three causes are explained."],
    )
    success_criteria = RubricSuccessCriteria(
        rubric_provided=True,
        criteria=[
            RubricCriterion(
                code=None,
                name="Knowledge & Understanding",
                teacher_wording="Demonstrates deep understanding of causes and consequences",
                student_friendly_meaning="Show you understand the causes and effects.",
                observable_evidence=["Names causes accurately."],
                top_band_requirements=["Demonstrates deep understanding."],
                good_vs_outstanding="Outstanding responses show nuanced understanding.",
                common_failure_modes=["Listing causes without explaining them."],
            )
        ],
        overall_top_band_profile="Deep, well-evidenced understanding throughout.",
        success_checklist=["Does my explanation show deep understanding, per Knowledge & Understanding?"],
        limitations=[],
    )

    await review_student_work(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        assignment_understanding=understanding,
        success_criteria=success_criteria,
        model=fake_model,
    )

    human_message = fake_model.structured.received[1]
    assert "Explain causes and evaluate consequences of the Industrial Revolution." in human_message.content
    assert "Demonstrates deep understanding of causes and consequences" in human_message.content


async def test_missing_rubric_and_context_handled_gracefully(sample_assignment, sample_student_work):
    fake_model = _FakeChatModel(SAMPLE_RESULT)

    result = await review_student_work(
        assignment=sample_assignment,
        student_work=sample_student_work,
        model=fake_model,
    )

    assert isinstance(result, StudentWorkReview)
    human_message = fake_model.structured.received[1]
    assert "Not provided." in human_message.content


def test_prompt_forbids_rewriting_and_requires_questions_not_answers():
    assert "Never write, rewrite, or supply a replacement sentence" in SYSTEM_PROMPT_TEXT
    assert "Do not write, rewrite, or supply replacement content" in SYSTEM_PROMPT_TEXT
    assert "never a rewritten sentence or an instruction in" in SYSTEM_PROMPT_TEXT
