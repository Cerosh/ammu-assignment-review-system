"""Live-model checks for Stage 3's review behaviour.

These call a real model, unlike test_student_work_review.py (which is fully
offline via a fake model). What they verify -- that the model actually
grounds strengths/issues/rubric assessment in the supplied material, phrases
challenges as questions rather than answers, and never asserts a confident
correction for a fact it can't verify -- is a property of real model
reasoning, not of the code's wiring.

Skipped automatically when no OPENAI_API_KEY is available, so the rest of
the suite stays runnable offline in any environment, including CI.
"""

import os
from pathlib import Path

import pytest

from ammu_review.assignment_understanding import review_assignment
from ammu_review.rubric_success_criteria import review_rubric_success_criteria
from ammu_review.student_work_review import review_student_work

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="requires a live OPENAI_API_KEY",
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
async def real_review():
    """Runs Stages 1-3 on the real Hannah Clarke case ONCE and shares the
    result across every test in this module -- these are real, billed model
    calls, so we don't want 5 separate tests each re-running the full
    3-stage pipeline for the same fixture."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric = (DATA_DIR / "hannah_clarke_rubric.md").read_text()
    student_work = (DATA_DIR / "hannah_clarke_student_work.md").read_text()

    understanding = await review_assignment(assignment=assignment, rubric=rubric)
    success_criteria = await review_rubric_success_criteria(
        assignment=assignment, rubric=rubric, assignment_understanding=understanding
    )
    return await review_student_work(
        assignment=assignment,
        student_work=student_work,
        rubric=rubric,
        assignment_understanding=understanding,
        success_criteria=success_criteria,
    )


async def test_strengths_and_issues_are_grounded_in_the_real_draft(real_review):
    """1. + 2. Strengths and issues trace to the actual submitted work, not
    generic praise/criticism."""
    result = real_review  # already computed by the fixture

    assert result.strengths, "must identify at least one strength"
    assert result.issues, "the real draft has real gaps -- must surface at least one issue"

    for issue in result.issues:
        assert issue.location.strip(), "every issue must point at a real location in the work"


async def test_rubric_assessment_preserves_stage2_criterion_codes(real_review):
    """5. Rubric alignment: assessed per the real rubric's own 3 outcome codes."""
    result = real_review  # already computed by the fixture

    codes = {c.criterion_code for c in result.rubric_assessment}
    assert codes == {"5.3", "5.8", "5.9"}


async def test_analysis_review_reflects_description_over_analysis(real_review):
    """7. The real draft is mostly narrative description -- WHAT should read
    stronger than WHY/SO WHAT, not uniformly generic."""
    result = real_review  # already computed by the fixture

    assert result.analysis_review.what.status in {"strong", "partial"}
    # At least one of the deeper dimensions should be flagged as weaker than
    # a purely descriptive narrative would earn on WHAT.
    assert result.analysis_review.so_what.status in {"partial", "missing"}


async def test_student_questions_are_phrased_as_questions_not_answers(real_review):
    """Guardrail: every student_question must be an actual question -- never
    a rewritten sentence or instruction in disguise."""
    result = real_review  # already computed by the fixture

    assert result.issues, "need at least one issue to check"
    for issue in result.issues:
        assert issue.student_question.strip().endswith("?"), (
            f"student_question must be a question, got: {issue.student_question!r}"
        )


async def test_issue_ids_are_unique_and_sequential(real_review):
    """Design requirement: Stage 3 output must be usable as Stage 4 input --
    each issue needs a stable, unique id."""
    result = real_review  # already computed by the fixture

    ids = [issue.id for issue in result.issues]
    assert ids == [f"S3-ISSUE-{i}" for i in range(1, len(ids) + 1)]


async def test_internal_contradiction_is_flagged_as_accuracy_issue():
    """6. An accuracy concern that CAN be established from the supplied
    material (an internal contradiction) must be caught."""
    assignment = (
        "# Task\n\nWrite a short report on the founding of Acme Robotics. "
        "The company was founded in 1990 by two engineers in Sydney.\n"
    )
    student_work = (
        "Acme Robotics was founded in 1995 by two engineers in Sydney. "
        "The company quickly grew into a major player in the robotics industry."
    )

    result = await review_student_work(assignment=assignment, student_work=student_work)

    accuracy_issues = [i for i in result.issues if i.category == "accuracy"]
    assert accuracy_issues, "a date that contradicts the assignment brief itself must be flagged"
    joined = " ".join(
        i.location + " " + i.observation + " " + i.why_it_matters for i in accuracy_issues
    ).lower()
    assert "1990" in joined or "1995" in joined


async def test_unverifiable_external_fact_is_not_confidently_corrected(real_review):
    """6. A specific factual claim that can ONLY be checked against external,
    real-world knowledge (not the supplied material) must not be silently
    "corrected" as if verified -- if raised at all, it must be hedged."""
    result = real_review  # already computed by the fixture

    accuracy_issues = [i for i in result.issues if i.category == "accuracy"]
    for issue in accuracy_issues:
        text = (issue.observation + " " + issue.why_it_matters + " " + issue.student_question).lower()
        if "burn" in text or "%" in text:
            hedge_words = ["verify", "double-check", "double check", "confirm", "cannot be sure", "check"]
            assert any(word in text for word in hedge_words), (
                "a claim only checkable against external facts must be hedged, not asserted as a "
                f"confirmed correction: {issue!r}"
            )
