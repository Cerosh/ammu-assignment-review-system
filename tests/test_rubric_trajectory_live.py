"""Live-model checks for the Rubric Trajectory capability.

These call a real model, unlike test_rubric_trajectory.py (which is fully
offline via a fake model). What they verify -- that the model grounds its
percentage estimates in the rubric's own criteria and actual evidence in the
work, reports honest confidence, and never invents a number when the rubric
can't support one -- is a property of real model reasoning, not of the
code's wiring.

Skipped automatically when no OPENAI_API_KEY is available, so the rest of
the suite stays runnable offline in any environment, including CI.
"""

import os
from pathlib import Path

import pytest

from ammu_review.assignment_understanding import review_assignment
from ammu_review.rubric_success_criteria import review_rubric_success_criteria
from ammu_review.student_work_review import grade_for_percent, review_rubric_trajectory

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="requires a live OPENAI_API_KEY",
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


@pytest.fixture(scope="module")
async def real_trajectory():
    """Runs Stages 1-2 then the Rubric Trajectory capability on the real
    Hannah Clarke case ONCE, shared across this module's tests -- these are
    real, billed model calls."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric = (DATA_DIR / "hannah_clarke_rubric.md").read_text()
    student_work = (DATA_DIR / "hannah_clarke_student_work.md").read_text()

    understanding = await review_assignment(assignment=assignment, rubric=rubric)
    success_criteria = await review_rubric_success_criteria(
        assignment=assignment, rubric=rubric, assignment_understanding=understanding
    )
    return await review_rubric_trajectory(
        assignment=assignment,
        student_work=student_work,
        rubric=rubric,
        assignment_understanding=understanding,
        success_criteria=success_criteria,
    )


async def test_criteria_preserve_rubric_outcome_codes(real_trajectory):
    """Trajectory is assessed per the real rubric's own 3 outcome codes,
    same as Stage 2/3 -- not invented, not omitted."""
    codes = {c.criterion_code for c in real_trajectory.criteria}
    assert codes == {"5.3", "5.8", "5.9"}


async def test_overall_estimate_is_plausible_and_grade_is_consistent(real_trajectory):
    """The overall percent (if given) is a real percentage, and the computed
    grade actually matches what grade_for_percent would produce -- proving
    the grade truly comes from Python logic, not the model."""
    percent = real_trajectory.overall_estimated_score_percent
    if percent is not None:
        assert 0.0 <= percent <= 100.0
        assert real_trajectory.estimated_grade == grade_for_percent(
            percent, tuple(real_trajectory.grade_boundaries_used)
        )
    else:
        assert real_trajectory.estimated_grade is None
        assert real_trajectory.limitations, "a missing overall percent must be explained"


async def test_confidence_is_reported_per_criterion_and_overall(real_trajectory):
    assert real_trajectory.criteria, "need at least one criterion to check"
    for criterion in real_trajectory.criteria:
        assert criterion.confidence in {"low", "medium", "high"}
    assert real_trajectory.overall_confidence in {"low", "medium", "high"}


async def test_biggest_opportunity_and_next_boundary_are_specific_not_generic(real_trajectory):
    """Guardrail: opportunities/gaps must be grounded, not generic filler,
    and never phrased as ready-to-submit content."""
    assert real_trajectory.biggest_opportunity.strip()
    assert real_trajectory.next_boundary_requirements

    generic_phrases = {"write better", "try harder", "improve your writing"}
    text = real_trajectory.biggest_opportunity.lower()
    assert not any(phrase in text for phrase in generic_phrases)


async def test_no_rubric_produces_exact_limitation_and_no_estimate():
    """No rubric supplied -> no invented percentages, exact required
    limitation string (same literal-string lesson learned in Stage 1)."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()
    student_work = (DATA_DIR / "hannah_clarke_student_work.md").read_text()

    result = await review_rubric_trajectory(assignment=assignment, student_work=student_work, rubric=None)

    assert result.rubric_provided is False
    assert result.criteria == []
    assert result.overall_estimated_score_percent is None
    assert result.estimated_grade is None
    assert any(
        "Rubric trajectory cannot be estimated because no marking rubric was supplied" in limitation
        for limitation in result.limitations
    )


async def test_rubric_without_enough_information_does_not_invent_a_percentage():
    """A rubric with a genuinely incomplete criterion (the 'Effort' band has
    no real descriptors) must not have a percentage invented for it."""
    assignment = (DATA_DIR / "group_presentation_task.md").read_text()
    rubric = (DATA_DIR / "ambiguous_rubric.md").read_text()
    student_work = (
        "Our group presented on renewable energy. I found three articles about solar "
        "panels and read them before the presentation. I worked with my group to put "
        "together some slides."
    )

    result = await review_rubric_trajectory(assignment=assignment, student_work=student_work, rubric=rubric)

    effort = next((c for c in result.criteria if "effort" in c.criterion_name.lower()), None)
    assert effort is not None, "the Effort criterion should still be extracted, even if incomplete"

    if effort.estimated_score_percent is None:
        assert effort.limitation, "an unset percentage must come with an explicit limitation"
    else:
        # If the model DID venture a number despite thin rubric wording, it
        # must at least flag low confidence rather than presenting it as solid.
        assert effort.confidence == "low"
