"""Application/session-layer models: Assignment, Draft, AssignmentSession.

These are NOT part of the review engine (Stages 1-5, frozen). They are the
application-layer concepts described in the Student Experience design
proposal that let the product track "one assignment, many drafts" on top of
the engine -- nothing here changes Stage 1-5 behaviour, schema, or
guardrails; it only wraps their existing structured outputs.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from ..assignment_understanding import AssignmentUnderstanding
from ..priority_coach import PriorityCoach
from ..rubric_success_criteria import RubricSuccessCriteria
from ..student_work_review import RubricTrajectory, StudentWorkReview
from ..toughest_teacher import ToughestTeacherReview


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Assignment(BaseModel):
    """One (task, rubric, teacher_instructions) triple, with Stage 1/2 output
    computed once and reused across every draft submitted against it."""

    id: str = Field(default_factory=_new_id)
    title: Optional[str] = None
    assignment_text: str
    rubric_text: Optional[str] = None
    teacher_instructions_text: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)

    assignment_understanding: Optional[AssignmentUnderstanding] = None
    success_criteria: Optional[RubricSuccessCriteria] = None


class Draft(BaseModel):
    """One snapshot of the student's work, plus everything computed for it."""

    id: str = Field(default_factory=_new_id)
    assignment_id: str
    draft_number: int
    student_work_text: str
    created_at: datetime = Field(default_factory=_now)

    student_work_review: Optional[StudentWorkReview] = None
    rubric_trajectory: Optional[RubricTrajectory] = None
    priority_coach: Optional[PriorityCoach] = None

    toughest_teacher_review: Optional[ToughestTeacherReview] = None
    # Which draft's PriorityCoach was actually checked when the Toughest
    # Teacher Challenge ran for THIS draft -- this draft's own id (nothing
    # earlier to check yet) or an earlier draft's id (the revision-check
    # case; see orchestration.challenge_draft / _resolve_priority_coach_for_challenge).
    priority_coach_checked_source_draft_id: Optional[str] = None


class AssignmentSession(BaseModel):
    """One assignment plus the full history of drafts submitted against it.

    This is the single unit of persistence -- see store.SessionStore.
    """

    assignment: Assignment
    drafts: list[Draft] = Field(default_factory=list)
