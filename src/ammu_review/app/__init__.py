"""Application/session layer: sits between the student experience (UI) and
the frozen review engine (Stages 1-5). Owns the Assignment/Draft concepts,
session persistence, stage orchestration (including previous-priority
carry-forward for the revision check), and the student-facing presentation
layer. See the Student Experience design proposal for the full rationale.
"""

from .models import Assignment, AssignmentSession, Draft
from .orchestration import challenge_draft, create_assignment, record_priority_viewed, submit_draft
from .presentation import (
    present_assignment_understanding,
    present_other_issues,
    present_priority,
    present_rubric_check,
    present_rubric_criterion,
    present_rubric_trajectory,
    present_strengths,
    present_success_criteria,
)
from .store import SessionStore

__all__ = [
    "Assignment",
    "AssignmentSession",
    "Draft",
    "SessionStore",
    "create_assignment",
    "submit_draft",
    "challenge_draft",
    "record_priority_viewed",
    "present_assignment_understanding",
    "present_rubric_criterion",
    "present_success_criteria",
    "present_priority",
    "present_rubric_trajectory",
    "present_rubric_check",
    "present_other_issues",
    "present_strengths",
]
