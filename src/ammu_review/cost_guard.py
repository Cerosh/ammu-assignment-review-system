"""Basic operation-count guard against accidental runaway LLM usage during
the private pilot.

This is deliberately NOT token/cost accounting -- see
.ai/PRODUCTION_READINESS.md "Cost protection" for why a simple operation
count is preferable to an inaccurate dollar estimate at this stage. It
guards exactly one action: submitting a draft/revision for review
(``submit_draft``, which costs 3 model calls -- Stage 3, Rubric Trajectory,
Stage 4). Two other expensive actions are deliberately NOT guarded here,
because each already has its own, sufficient protection:

- Stage 5 (``challenge_draft``, the "Toughest Teacher" action) -- ui/app.py
  only ever offers that button while ``draft.toughest_teacher_review is
  None``, so it can run at most once per draft regardless of this guard.
- Assignment creation (``create_assignment``, Stage 1 + 2) -- unlike a
  button on an already-loaded page, this requires re-entering the
  assignment/rubric text by hand each time, which is a much weaker
  "accidental repeat" risk.
"""

from __future__ import annotations

import os

DEFAULT_MAX_DRAFTS_PER_ASSIGNMENT = 10

MAX_DRAFTS_ENV_VAR = "AMMU_MAX_DRAFTS_PER_ASSIGNMENT"


def get_max_drafts_per_assignment() -> int:
    """The configured cap, or the default if unset/invalid.

    Generous by design: the intended workflow is understand -> draft ->
    revise -> maybe revise again -> optionally challenge, so even a
    thorough student rarely submits more than 2-3 drafts for one
    assignment. A default of 10 comfortably covers that with room to
    spare, while still stopping runaway/accidental repeated submissions
    well before real cost accumulates. A non-positive or non-numeric
    configured value falls back to the default rather than disabling the
    guard entirely -- there's no legitimate deployment reason to want
    zero drafts allowed, and treating a misconfigured value as "no limit"
    would be the wrong failure direction for a cost guard.
    """
    raw = os.getenv(MAX_DRAFTS_ENV_VAR)
    if raw is None:
        return DEFAULT_MAX_DRAFTS_PER_ASSIGNMENT
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_MAX_DRAFTS_PER_ASSIGNMENT
    return value if value > 0 else DEFAULT_MAX_DRAFTS_PER_ASSIGNMENT


def has_reached_draft_limit(current_draft_count: int) -> bool:
    """True once ``current_draft_count`` existing drafts already meet or
    exceed the configured limit -- callers should block submitting one
    more, not any of the drafts already there."""
    return current_draft_count >= get_max_drafts_per_assignment()
