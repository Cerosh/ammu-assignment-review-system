"""Application-layer orchestration on top of the frozen review engine.

This module owns NO review logic of its own -- it only calls the existing
Stage 1-5 functions in the right order, wraps their output in the
Assignment/Draft session model, and persists progress after each stage so a
crash mid-pipeline doesn't lose an already-paid-for model call. See the
Student Experience design proposal (Phase A) for the rationale, especially
section 7 for why ``challenge_draft`` carries a *previous* draft's
PriorityCoach forward instead of the current one.

It also emits telemetry events (see .ai/TELEMETRY.md) at each meaningful
step -- this is the ONLY integration point between the application layer
and telemetry; Stage 1-5 modules never import telemetry and telemetry never
imports them. A telemetry write failure never breaks a review: TelemetryRecorder
catches and logs its own errors internally, so orchestration calls
``record()`` unconditionally.
"""

from __future__ import annotations

import time
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel

from ..assignment_understanding import review_assignment
from ..priority_coach import PriorityCoach, review_priority_coach
from ..rubric_success_criteria import review_rubric_success_criteria
from ..student_work_review import review_rubric_trajectory, review_student_work
from ..telemetry import EventType, TelemetryRecorder
from ..toughest_teacher import review_toughest_teacher
from .models import Assignment, AssignmentSession, Draft
from .store import SessionStore


async def create_assignment(
    store: SessionStore,
    assignment_text: str,
    rubric_text: Optional[str] = None,
    teacher_instructions_text: Optional[str] = None,
    title: Optional[str] = None,
    model: Optional[BaseChatModel] = None,
    recorder: Optional[TelemetryRecorder] = None,
) -> AssignmentSession:
    """Run Stage 1 + Stage 2 once for a new assignment and persist the session."""
    recorder = recorder or TelemetryRecorder()

    understanding = await review_assignment(
        assignment=assignment_text,
        rubric=rubric_text,
        teacher_instructions=teacher_instructions_text,
        model=model,
    )
    assignment = Assignment(
        title=title,
        assignment_text=assignment_text,
        rubric_text=rubric_text,
        teacher_instructions_text=teacher_instructions_text,
        assignment_understanding=understanding,
    )
    session = AssignmentSession(assignment=assignment)
    store.save(session)  # persist Stage 1's result before paying for Stage 2
    recorder.record(EventType.ASSIGNMENT_CREATED, assignment_id=assignment.id)

    success_criteria = await review_rubric_success_criteria(
        assignment=assignment_text,
        rubric=rubric_text,
        teacher_instructions=teacher_instructions_text,
        assignment_understanding=understanding,
        model=model,
    )
    session.assignment.success_criteria = success_criteria
    store.save(session)
    recorder.record(
        EventType.ASSIGNMENT_UNDERSTOOD,
        assignment_id=assignment.id,
        metadata={"rubric_provided": success_criteria.rubric_provided},
    )

    return session


async def submit_draft(
    store: SessionStore,
    assignment_id: str,
    student_work_text: str,
    model: Optional[BaseChatModel] = None,
    recorder: Optional[TelemetryRecorder] = None,
) -> Draft:
    """Run Stage 3 -> Rubric Trajectory -> Stage 4 for a new draft."""
    recorder = recorder or TelemetryRecorder()
    session = store.load(assignment_id)
    assignment = session.assignment

    draft = Draft(
        assignment_id=assignment_id,
        draft_number=len(session.drafts) + 1,
        student_work_text=student_work_text,
    )
    session.drafts.append(draft)
    store.save(session)  # persist the raw submission immediately

    recorder.record(
        EventType.DRAFT_SUBMITTED,
        assignment_id=assignment_id,
        draft_id=draft.id,
        metadata={"draft_number": draft.draft_number, "word_count": len(student_work_text.split())},
    )
    if draft.draft_number > 1:
        previous_draft = session.drafts[-2]
        recorder.record(
            EventType.REVISION_SUBMITTED,
            assignment_id=assignment_id,
            draft_id=draft.id,
            metadata={
                "previous_draft_id": previous_draft.id,
                "new_draft_id": draft.id,
                "draft_number": draft.draft_number,
            },
        )

    recorder.record(EventType.REVIEW_STARTED, assignment_id=assignment_id, draft_id=draft.id)
    review_start = time.monotonic()

    try:
        work_review = await review_student_work(
            assignment=assignment.assignment_text,
            student_work=student_work_text,
            rubric=assignment.rubric_text,
            teacher_instructions=assignment.teacher_instructions_text,
            assignment_understanding=assignment.assignment_understanding,
            success_criteria=assignment.success_criteria,
            model=model,
        )
        draft.student_work_review = work_review
        store.save(session)

        trajectory = await review_rubric_trajectory(
            assignment=assignment.assignment_text,
            student_work=student_work_text,
            rubric=assignment.rubric_text,
            teacher_instructions=assignment.teacher_instructions_text,
            assignment_understanding=assignment.assignment_understanding,
            success_criteria=assignment.success_criteria,
            model=model,
        )
        draft.rubric_trajectory = trajectory
        store.save(session)

        priority = await review_priority_coach(
            assignment=assignment.assignment_text,
            student_work=student_work_text,
            rubric=assignment.rubric_text,
            teacher_instructions=assignment.teacher_instructions_text,
            assignment_understanding=assignment.assignment_understanding,
            success_criteria=assignment.success_criteria,
            student_work_review=work_review,
            rubric_trajectory=trajectory,
            model=model,
        )
        draft.priority_coach = priority
        store.save(session)
    except Exception as exc:
        recorder.record(
            EventType.REVIEW_COMPLETED,
            assignment_id=assignment_id,
            draft_id=draft.id,
            metadata={
                "success": False,
                "duration_ms": int((time.monotonic() - review_start) * 1000),
                "error_type": type(exc).__name__,
            },
        )
        raise

    duration_ms = int((time.monotonic() - review_start) * 1000)
    recorder.record(
        EventType.REVIEW_COMPLETED,
        assignment_id=assignment_id,
        draft_id=draft.id,
        metadata={
            "success": True,
            "duration_ms": duration_ms,
            "stages_completed": ["student_work_review", "rubric_trajectory", "priority_coach"],
            "model_call_count": 3,
            "issue_count": len(work_review.issues),
            "limitation_count": (
                len(work_review.limitations) + len(trajectory.limitations) + len(priority.limitations)
            ),
        },
    )
    recorder.record(
        EventType.PRIORITY_SELECTED,
        assignment_id=assignment_id,
        draft_id=draft.id,
        metadata={
            "priority_issue_id": priority.priority_issue_id,
            "priority_category": priority.priority_category,
            "criterion_code": priority.primary_criterion.criterion_code,
            "current_grade": priority.current_grade,
            "target_grade": priority.target_grade,
        },
    )

    return draft


def _resolve_priority_coach_for_challenge(
    session: AssignmentSession, draft: Draft
) -> tuple[Optional[PriorityCoach], str]:
    """Which draft's priority should Stage 5 check against this draft?

    If an earlier draft exists, its PriorityCoach is the thing that was
    supposed to be fixed by the time this draft was written -- checking THAT
    against this draft's fresh Stage 3/Trajectory context is what makes
    "review again" meaningful without a full revision-tracking loop (Student
    Experience design proposal, section 7). The first draft has nothing
    earlier to check, so it falls back to checking its own priority.
    """
    index = next(i for i, d in enumerate(session.drafts) if d.id == draft.id)
    if index == 0:
        return draft.priority_coach, draft.id
    previous_draft = session.drafts[index - 1]
    return previous_draft.priority_coach, previous_draft.id


async def challenge_draft(
    store: SessionStore,
    assignment_id: str,
    draft_id: str,
    model: Optional[BaseChatModel] = None,
    recorder: Optional[TelemetryRecorder] = None,
) -> Draft:
    """Run Stage 5 (Toughest Teacher Review) for one draft, on demand."""
    recorder = recorder or TelemetryRecorder()
    session = store.load(assignment_id)
    assignment = session.assignment
    try:
        draft = next(d for d in session.drafts if d.id == draft_id)
    except StopIteration:
        raise ValueError(f"No draft with id '{draft_id}' found for assignment '{assignment_id}'.") from None

    priority_coach_to_check, source_draft_id = _resolve_priority_coach_for_challenge(session, draft)

    recorder.record(
        EventType.PRIORITY_CHALLENGE_STARTED,
        assignment_id=assignment_id,
        draft_id=draft.id,
        metadata={"priority_coach_source_draft_id": source_draft_id},
    )
    challenge_start = time.monotonic()

    try:
        review = await review_toughest_teacher(
            assignment=assignment.assignment_text,
            student_work=draft.student_work_text,
            rubric=assignment.rubric_text,
            teacher_instructions=assignment.teacher_instructions_text,
            assignment_understanding=assignment.assignment_understanding,
            success_criteria=assignment.success_criteria,
            student_work_review=draft.student_work_review,
            rubric_trajectory=draft.rubric_trajectory,
            priority_coach=priority_coach_to_check,
            model=model,
        )
    except Exception as exc:
        recorder.record(
            EventType.PRIORITY_CHALLENGE_COMPLETED,
            assignment_id=assignment_id,
            draft_id=draft.id,
            metadata={
                "success": False,
                "duration_ms": int((time.monotonic() - challenge_start) * 1000),
                "error_type": type(exc).__name__,
            },
        )
        raise

    draft.toughest_teacher_review = review
    draft.priority_coach_checked_source_draft_id = source_draft_id
    store.save(session)

    trajectory_changed: Optional[bool] = None
    if source_draft_id != draft.id:
        source_draft = next((d for d in session.drafts if d.id == source_draft_id), None)
        source_grade = (
            source_draft.rubric_trajectory.estimated_grade
            if source_draft is not None and source_draft.rubric_trajectory is not None
            else None
        )
        current_grade = draft.rubric_trajectory.estimated_grade if draft.rubric_trajectory is not None else None
        if source_grade is not None and current_grade is not None:
            trajectory_changed = source_grade != current_grade

    recorder.record(
        EventType.PRIORITY_CHALLENGE_COMPLETED,
        assignment_id=assignment_id,
        draft_id=draft.id,
        metadata={
            "success": True,
            "duration_ms": int((time.monotonic() - challenge_start) * 1000),
            "previous_priority_issue_id": (
                priority_coach_to_check.priority_issue_id if priority_coach_to_check is not None else None
            ),
            "priority_status": review.priority_status,
            "current_grade": review.current_grade,
            "trajectory_changed": trajectory_changed,
        },
    )

    return draft
