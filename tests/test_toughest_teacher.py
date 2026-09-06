"""Tests for Stage 5: Toughest Teacher Review.

These tests never call a live model -- they substitute a fake chat model so
the suite runs offline and deterministically. What they verify is the wiring
(all source material and AI-generated context reach the model), the
structured output contract, and -- crucially -- the Python-side safety net
that a real model needs but a fake one lets us test precisely:

- current_grade/priority_coach_issue_id are echoed from upstream results in
  Python, never invented by the model.
- a hallucinated/mismatched issue_id inside unresolved_issues is caught and
  discarded, with its category overridden from the real Stage 3 issue when
  valid.
- question-format and no-invented-percentage guardrails are enforced (as
  limitations, never by silently rewriting the model's text).

Whether the model's own judgement is actually sound (fair, not manufactured,
genuinely checks Stage 4's priority) is checked in
test_toughest_teacher_live.py.
"""

from pathlib import Path

import pytest

from ammu_review.priority_coach import CriterionRef, PriorityCoach
from ammu_review.rubric_success_criteria import RubricCriterion, RubricSuccessCriteria
from ammu_review.student_work_review import (
    AnalysisReview,
    DimensionReview,
    ReviewIssue,
    RubricTrajectory,
    StudentWorkReview,
)
from ammu_review.toughest_teacher import (
    SYSTEM_PROMPT_TEXT,
    TeacherChallenge,
    ToughestTeacherReview,
    _ToughestTeacherDraft,
    review_toughest_teacher,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _dimension(status: str = "partial") -> DimensionReview:
    return DimensionReview(status=status, observation="Some observation.")


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

SAMPLE_PRIORITY_COACH = PriorityCoach(
    priority_issue_id="S3-ISSUE-2",
    priority_statement="The analysis of whether justice was served lacks depth.",
    priority_category="rubric",
    why_this_matters="This is the core analytical requirement of the task.",
    primary_criterion=CriterionRef(criterion_code="5.9", criterion_name="Works independently and collaboratively"),
    also_affects_criteria=[],
    trajectory_connection="Addressing this is likely to strengthen your position toward the B range.",
    student_question="What evidence from the case could help you evaluate whether justice was served?",
    improvement_target="Your analysis should move beyond stating an outcome and justify it with evidence.",
    evidence_to_consider=["The specific circumstances of how the case concluded."],
    other_issues_deferred=["S3-ISSUE-1"],
    confidence="medium",
    limitations=[],
    current_grade="C",
    target_grade="B",
)

SAMPLE_DRAFT = _ToughestTeacherDraft(
    overall_judgment="The work shows a solid narrative but the core legal analysis remains underdeveloped.",
    trajectory_challenge="The C estimate looks justified -- the analysis of justice served is still surface-level.",
    priority_status="unresolved",
    priority_status_explanation="The justice-served analysis still lacks a justified evaluation.",
    unresolved_issues=[
        TeacherChallenge(
            rank=1,
            issue_id="S3-ISSUE-2",
            category="analysis",  # deliberately wrong -- should be overwritten to "rubric" from the real issue
            related_criteria=[CriterionRef(criterion_code="5.9", criterion_name="Works independently and collaboratively")],
            observation="The conclusion about justice states an outcome without justifying it.",
            why_it_matters="This is the rubric's core analytical requirement.",
            teacher_challenge="I would push back on whether this conclusion is actually earned by the evidence.",
            student_question="What specific evidence would justify your conclusion about whether justice was served?",
        )
    ],
    resolved_or_adequately_addressed=["The case summary is now clear and detailed."],
    evidence_that_supports_judgment=["The narrative covers the key events in order."],
    what_would_change_my_mind=["A clear justification linking the outcome to the legal concepts discussed."],
    final_student_question="What specific evidence would justify your conclusion about whether justice was served?",
    final_improvement_target="Your conclusion should be explicitly justified by evidence, not just stated.",
    confidence="medium",
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
        assert schema is _ToughestTeacherDraft
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


# --- public API / structured output shape ----------------------------------


async def test_returns_structured_output_with_echoed_context(sample_assignment, sample_rubric, sample_student_work):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)

    result = await review_toughest_teacher(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        rubric_trajectory=SAMPLE_TRAJECTORY,
        priority_coach=SAMPLE_PRIORITY_COACH,
        model=fake_model,
    )

    assert isinstance(result, ToughestTeacherReview)
    # Echoed straight from upstream results in Python, never invented.
    assert result.current_grade == "C"
    assert result.priority_coach_issue_id == "S3-ISSUE-2"


async def test_valid_issue_id_overrides_category_from_real_stage3_issue(
    sample_assignment, sample_rubric, sample_student_work
):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)

    result = await review_toughest_teacher(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        model=fake_model,
    )

    challenge = result.unresolved_issues[0]
    assert challenge.issue_id == "S3-ISSUE-2"
    # SAMPLE_DRAFT said "analysis" but the real S3-ISSUE-2 is "rubric" -- Python must win.
    assert challenge.category == "rubric"
    assert not any("S3-ISSUE-2" in limitation and "does not match" in limitation for limitation in result.limitations)


async def test_invalid_issue_id_is_discarded_and_logged(sample_assignment, sample_rubric, sample_student_work):
    bad_challenge = SAMPLE_DRAFT.unresolved_issues[0].model_copy(update={"issue_id": "S3-ISSUE-999"})
    bad_draft = SAMPLE_DRAFT.model_copy(update={"unresolved_issues": [bad_challenge]})
    fake_model = _FakeChatModel(bad_draft)

    result = await review_toughest_teacher(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        model=fake_model,
    )

    assert result.unresolved_issues[0].issue_id is None
    assert any("S3-ISSUE-999" in limitation for limitation in result.limitations)
    # No real issue to defer to -- the model's own (unvalidated) category is kept.
    assert result.unresolved_issues[0].category == "analysis"


async def test_no_student_work_review_forces_issue_ids_none(sample_assignment, sample_rubric, sample_student_work):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)  # SAMPLE_DRAFT's challenge has issue_id set

    result = await review_toughest_teacher(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=None,
        model=fake_model,
    )

    assert result.unresolved_issues[0].issue_id is None
    assert any("S3-ISSUE-2" in limitation for limitation in result.limitations)


async def test_no_priority_coach_forces_priority_status_none_even_if_model_invents_one(
    sample_assignment, sample_rubric, sample_student_work
):
    """The model must not be trusted to know priority_status is unknowable
    when no priority_coach was supplied -- Python enforces this from ground
    truth (was priority_coach actually passed in), not the model's claim."""
    bad_draft = SAMPLE_DRAFT.model_copy(update={"priority_status": "unresolved"})
    fake_model = _FakeChatModel(bad_draft)

    result = await review_toughest_teacher(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        priority_coach=None,
        model=fake_model,
    )

    assert result.priority_status is None
    assert any("priority_status" in limitation and "unresolved" in limitation for limitation in result.limitations)


async def test_no_rubric_trajectory_or_priority_coach_leaves_context_none(
    sample_assignment, sample_rubric, sample_student_work
):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)

    result = await review_toughest_teacher(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        rubric_trajectory=None,
        priority_coach=None,
        model=fake_model,
    )

    assert result.current_grade is None
    assert result.priority_coach_issue_id is None
    human_message = fake_model.structured.received[1]
    assert "Not available -- no Rubric Trajectory context was supplied." in human_message.content
    assert "Not available -- no Stage 4 Priority Coach context was supplied." in human_message.content


# --- guardrail validation ----------------------------------------------------


async def test_question_not_ending_in_question_mark_is_flagged_not_silently_fixed(
    sample_assignment, sample_rubric, sample_student_work
):
    bad_draft = SAMPLE_DRAFT.model_copy(
        update={"final_student_question": "This is not phrased as a question."}
    )
    fake_model = _FakeChatModel(bad_draft)

    result = await review_toughest_teacher(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        model=fake_model,
    )

    # Never silently rewritten -- the text is unchanged, but the violation is logged.
    assert result.final_student_question == "This is not phrased as a question."
    assert any("final_student_question" in limitation for limitation in result.limitations)


async def test_invented_percentage_in_trajectory_challenge_is_flagged(
    sample_assignment, sample_rubric, sample_student_work
):
    bad_draft = SAMPLE_DRAFT.model_copy(
        update={"trajectory_challenge": "This means the student is actually at 62% overall."}
    )
    fake_model = _FakeChatModel(bad_draft)

    result = await review_toughest_teacher(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        rubric_trajectory=SAMPLE_TRAJECTORY,
        model=fake_model,
    )

    assert "62%" in result.trajectory_challenge  # never silently stripped
    assert any("trajectory_challenge" in limitation and "percentage" in limitation for limitation in result.limitations)


async def test_criterion_code_not_in_success_criteria_is_flagged(sample_assignment, sample_rubric, sample_student_work):
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
    fake_model = _FakeChatModel(SAMPLE_DRAFT)  # SAMPLE_DRAFT's challenge references criterion "5.9", not "5.3"

    result = await review_toughest_teacher(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        success_criteria=success_criteria,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        model=fake_model,
    )

    assert any("5.9" in limitation and "does not match any criterion" in limitation for limitation in result.limitations)


# --- wiring ------------------------------------------------------------------


async def test_all_context_reaches_the_model(sample_assignment, sample_rubric, sample_student_work):
    fake_model = _FakeChatModel(SAMPLE_DRAFT)

    await review_toughest_teacher(
        assignment=sample_assignment,
        student_work=sample_student_work,
        rubric=sample_rubric,
        student_work_review=SAMPLE_STUDENT_WORK_REVIEW,
        rubric_trajectory=SAMPLE_TRAJECTORY,
        priority_coach=SAMPLE_PRIORITY_COACH,
        model=fake_model,
    )

    human_message = fake_model.structured.received[1]
    assert sample_assignment.strip() in human_message.content
    assert sample_rubric.strip() in human_message.content
    assert sample_student_work.strip() in human_message.content
    assert "justice analysis lacks depth" in human_message.content  # from SAMPLE_STUDENT_WORK_REVIEW
    assert "Link the case outcome more explicitly" in human_message.content  # from SAMPLE_TRAJECTORY
    assert "core analytical requirement of the task" in human_message.content  # from SAMPLE_PRIORITY_COACH
    assert "Current estimated position (from Rubric Trajectory): C" in human_message.content
    assert "Stage 4's selected priority issue id" in human_message.content and "S3-ISSUE-2" in human_message.content


def test_prompt_guardrails_are_present():
    assert "Ammu owns the work. The system owns the challenge." in SYSTEM_PROMPT_TEXT
    assert "NO SCORE PREDICTION" in SYSTEM_PROMPT_TEXT
    assert "never a new number" in SYSTEM_PROMPT_TEXT or "never state a new percentage" in SYSTEM_PROMPT_TEXT.lower()
    assert "Do not repeat an issue that has genuinely been resolved." in SYSTEM_PROMPT_TEXT
