"""Live-model checks for Stage 2's rubric-grounding behaviour.

These call a real model, unlike test_rubric_success_criteria.py (which is
fully offline via a fake model). What they verify -- that the model
extracts the rubric's own criteria/codes rather than inventing or
generalising them -- is a property of real model reasoning, not of the
code's wiring. A fake model would just echo back whatever canned response
we hardcoded, which would prove nothing about whether the prompt works.

Skipped automatically when no OPENAI_API_KEY is available, so the rest of
the suite (test_rubric_success_criteria.py) stays runnable offline in any
environment, including CI.
"""

import os
from pathlib import Path

import pytest

from ammu_review.assignment_understanding import review_assignment
from ammu_review.rubric_success_criteria import review_rubric_success_criteria

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="requires a live OPENAI_API_KEY",
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

_GENERIC_TAXONOMY = {
    "knowledge",
    "understanding",
    "analysis",
    "evidence",
    "evaluation",
    "communication",
}


async def test_criteria_preserve_rubric_outcome_codes_and_names():
    """1. + 4. + 8. Real Hannah Clarke rubric: codes preserved, none invented,
    none omitted -- exactly the 3 outcomes the rubric actually contains."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric = (DATA_DIR / "hannah_clarke_rubric.md").read_text()

    result = await review_rubric_success_criteria(assignment=assignment, rubric=rubric)

    assert result.rubric_provided is True
    codes = {c.code for c in result.criteria}
    assert codes == {"5.3", "5.8", "5.9"}
    assert len(result.criteria) == 3


async def test_top_band_requirements_come_from_the_actual_highest_band():
    """2. Top-band requirements are grounded in this rubric's own Outstanding
    descriptors, not a generic 'do it well' restatement."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric = (DATA_DIR / "hannah_clarke_rubric.md").read_text()

    result = await review_rubric_success_criteria(assignment=assignment, rubric=rubric)

    by_code = {c.code: c for c in result.criteria}

    joined_59 = " ".join(by_code["5.9"].top_band_requirements).lower()
    assert "wide range of reasons" in joined_59 or "extensive" in joined_59

    joined_58 = " ".join(by_code["5.8"].top_band_requirements).lower()
    assert "intensively researched" in joined_58 or "broad range of media" in joined_58


async def test_criteria_names_are_not_a_generic_taxonomy():
    """3. Criterion names are the rubric's own wording, not Knowledge/
    Understanding/Analysis/Evidence/Evaluation/Communication."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric = (DATA_DIR / "hannah_clarke_rubric.md").read_text()

    result = await review_rubric_success_criteria(assignment=assignment, rubric=rubric)

    for criterion in result.criteria:
        assert criterion.name.strip().lower() not in _GENERIC_TAXONOMY


async def test_success_checklist_is_not_a_restatement_of_stage1_task_steps():
    """Stage 2 must be genuinely different from Stage 1 -- its checklist should
    be rubric self-checks, not a repeat of the assignment's procedural steps
    (which Stage 1 already covers in its own `checklist`/`requirements`)."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric = (DATA_DIR / "hannah_clarke_rubric.md").read_text()

    understanding = await review_assignment(assignment=assignment, rubric=rubric)
    result = await review_rubric_success_criteria(
        assignment=assignment,
        rubric=rubric,
        assignment_understanding=understanding,
    )

    checklist_text = " ".join(result.success_checklist).lower()

    # Task-procedure phrasing (Stage 1's territory) should not dominate the checklist.
    assert not ("collect" in checklist_text and "media articles" in checklist_text)
    assert not ("choose" in checklist_text and "area of law" in checklist_text)

    # It should instead be tied to the rubric's own criteria.
    assert any(code in checklist_text for code in ["5.3", "5.8", "5.9"])


async def test_missing_rubric_produces_no_criteria_and_explicit_limitation():
    """5. No rubric supplied -> no invented criteria, explicit limitation instead."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()

    result = await review_rubric_success_criteria(assignment=assignment, rubric=None)

    assert result.rubric_provided is False
    assert result.criteria == []
    assert result.limitations, "limitations must not be empty when no rubric was supplied"
    assert any("rubric" in limitation.lower() for limitation in result.limitations)


async def test_ambiguous_rubric_states_the_limitation_instead_of_guessing():
    """6. A rubric with a genuinely incomplete criterion ('Effort' has no real
    Sound/High descriptors) must not have its gaps silently filled in."""
    assignment = (DATA_DIR / "group_presentation_task.md").read_text()
    rubric = (DATA_DIR / "ambiguous_rubric.md").read_text()

    result = await review_rubric_success_criteria(assignment=assignment, rubric=rubric)

    effort = next((c for c in result.criteria if "effort" in c.name.lower()), None)
    assert effort is not None, "the Effort criterion should still be extracted, even if incomplete"

    effort_text = " ".join(
        [effort.good_vs_outstanding, *effort.top_band_requirements]
    ).lower()
    limitations_text = " ".join(result.limitations).lower()

    flagged_as_ambiguous = (
        "cannot" in effort_text
        or "unclear" in effort_text
        or "not clear" in effort_text
        or "discretion" in effort_text
        or "ambiguous" in limitations_text
        or "effort" in limitations_text
        or "incomplete" in limitations_text
    )
    assert flagged_as_ambiguous, (
        "an incomplete rubric criterion must be flagged as a limitation, not "
        "silently filled in with an invented distinction"
    )
