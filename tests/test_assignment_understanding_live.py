"""Live-model checks for Stage 1's rubric-grounding behaviour.

These call a real model, unlike test_assignment_understanding.py (which is
fully offline via a fake model). What they verify -- that the model actually
grounds `assessed_skills` / `top_band_thinking` in the supplied rubric's own
terminology instead of a generic taxonomy -- is a property of real model
reasoning, not of the code's wiring. A fake model would just echo back
whatever canned response we hardcoded, which would prove nothing about
whether the prompt change actually works.

Skipped automatically when no OPENAI_API_KEY is available, so the rest of
the suite (test_assignment_understanding.py) stays runnable offline in any
environment, including CI.
"""

import os
from pathlib import Path

import pytest

from ammu_review.assignment_understanding import review_assignment

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


def _is_generic_only(items: list[str]) -> bool:
    """True if every item is just a bare generic-taxonomy word."""
    return all(item.strip().lower().rstrip(".:") in _GENERIC_TAXONOMY for item in items)


async def test_assessed_skills_use_rubric_outcome_codes():
    """A. Rubric with explicit outcome codes/names -> they appear verbatim."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric = (DATA_DIR / "hannah_clarke_rubric.md").read_text()

    result = await review_assignment(assignment=assignment, rubric=rubric)

    joined = " ".join(result.assessed_skills)
    assert "5.3" in joined
    assert "5.8" in joined
    assert "5.9" in joined
    assert not _is_generic_only(result.assessed_skills)


async def test_top_band_thinking_grounded_in_rubric_not_generic():
    """B. top_band_thinking reflects this rubric's own top-band descriptors."""
    assignment = (DATA_DIR / "hannah_clarke_task.md").read_text()
    rubric = (DATA_DIR / "hannah_clarke_rubric.md").read_text()

    result = await review_assignment(assignment=assignment, rubric=rubric)

    joined = " ".join(result.top_band_thinking).lower()
    assert any(
        phrase in joined
        for phrase in [
            "extensive",
            "intensively researched",
            "wide range of reasons",
            "outstanding understanding",
            "broad range of media",
        ]
    )


async def test_rubric_without_outcome_codes_uses_its_own_wording():
    """C. Rubric with named criteria but no codes -> its own wording is used."""
    assignment = (DATA_DIR / "sample_assignment.md").read_text()
    rubric = (DATA_DIR / "no_code_rubric.md").read_text()

    result = await review_assignment(assignment=assignment, rubric=rubric)

    joined = " ".join(result.assessed_skills).lower()
    assert any(
        phrase in joined
        for phrase in ["historical explanation", "source use", "written expression"]
    )


async def test_missing_rubric_does_not_invent_assessment_criteria():
    """D. No rubric supplied -> no invented assessment criteria, and no silent
    empty list either -- an explicit "cannot be determined" statement."""
    assignment = (DATA_DIR / "sample_assignment.md").read_text()

    result = await review_assignment(assignment=assignment, rubric=None)

    assert result.assessed_skills, "assessed_skills must not be silently empty"
    skills_joined = " ".join(result.assessed_skills).lower()
    assert "cannot be determined" in skills_joined and "marking rubric" in skills_joined

    top_band_joined = " ".join(result.top_band_thinking).lower()
    assert "cannot be determined" in top_band_joined and "marking rubric" in top_band_joined
