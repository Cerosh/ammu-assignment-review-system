"""Student-facing presentation/translation layer.

Pure functions: structured Stage 1/2 output in, plain dicts of Grade-9
friendly strings out. No AI calls happen here -- this is templating over
already-computed fields, not a new review capability. Keeping this separate
from any UI framework means the UI layer never touches a Stage 1-5 field
name directly (see the Student Experience design proposal, sections 8 and
16).

Stage 1 (Assignment Understanding) and Stage 2 (Rubric / Success Criteria)
translators below serve Screens A/B. Stage 3 (Student Work Review), Rubric
Trajectory, and Stage 4 (Priority Coach) translators below serve Screen C
("Your Review"). Stage 5 (Toughest Teacher) translators serve Screen D
("Toughest Teacher").
"""

from __future__ import annotations

from typing import Optional

from ..assignment_understanding import AssignmentUnderstanding
from ..priority_coach import PriorityCoach
from ..rubric_success_criteria import RubricCriterion, RubricSuccessCriteria
from ..student_work_review import RubricTrajectory, StudentWorkReview, grade_for_percent
from ..toughest_teacher import ToughestTeacherReview

_CATEGORY_LABELS = {
    "content": "What you wrote",
    "evidence": "Your evidence",
    "analysis": "Your thinking and analysis",
    "accuracy": "Getting the facts right",
    "structure": "How it's organised",
    "grammar": "Grammar and wording",
    "rubric": "Meeting the rubric",
}


def _translate_category(category: str) -> str:
    return _CATEGORY_LABELS.get(category, category)


def present_rubric_criterion(criterion: RubricCriterion) -> dict:
    return {
        "code": criterion.code,
        "name": criterion.name,
        "what_it_means": criterion.student_friendly_meaning,
        "what_top_marks_need": criterion.top_band_requirements,
        "good_vs_outstanding": criterion.good_vs_outstanding,
        "common_mistakes": criterion.common_failure_modes,
    }


def present_assignment_understanding(understanding: AssignmentUnderstanding) -> dict:
    return {
        "what_youre_being_asked_to_do": understanding.main_task,
        "requirements": understanding.requirements,
        "checklist": understanding.checklist,
        "watch_out_for": understanding.hidden_traps,
        "key_words_to_notice": understanding.command_words,
    }


def present_success_criteria(success_criteria: RubricSuccessCriteria) -> dict:
    if not success_criteria.rubric_provided:
        return {
            "rubric_provided": False,
            "message": (
                "No marking rubric was given for this task, so this is based "
                "on the task sheet alone."
            ),
            "criteria": [],
            "checklist": success_criteria.success_checklist,
            "limitations": success_criteria.limitations,
        }
    return {
        "rubric_provided": True,
        "overview": success_criteria.overall_top_band_profile,
        "criteria": [present_rubric_criterion(c) for c in success_criteria.criteria],
        "checklist": success_criteria.success_checklist,
        "limitations": success_criteria.limitations,
    }


# --- Screen C: "Your Review" ---------------------------------------------------
#
# Translators for Stage 3 (Student Work Review), Rubric Trajectory, and
# Stage 4 (Priority Coach). Deliberately never expose a raw issue id,
# criterion object, or model field name -- only plain strings/dicts a
# Grade-9 student would actually read. No AI calls happen here.


def present_priority(priority_coach: Optional[PriorityCoach]) -> dict:
    """Tier 1: the ONE thing to fix. Never exposes priority_issue_id or the
    raw priority_category -- only the coaching language and the rubric
    criterion it's tied to."""
    if priority_coach is None:
        return {"available": False}
    return {
        "available": True,
        "priority_statement": priority_coach.priority_statement,
        "why_it_matters": priority_coach.why_this_matters,
        "criterion": {
            "code": priority_coach.primary_criterion.criterion_code,
            "name": priority_coach.primary_criterion.criterion_name,
        },
        "student_question": priority_coach.student_question,
    }


def present_rubric_trajectory(trajectory: Optional[RubricTrajectory]) -> dict:
    """Tier 2: where you stand. Never invents a grade -- a per-criterion
    grade is only shown when the trajectory itself supplied a percentage,
    computed via the SAME deterministic grade_for_percent()/boundaries the
    engine already used for the overall estimate, never a new calculation."""
    if trajectory is None:
        return {"available": False, "message": "We don't have a rubric trajectory for this draft yet."}
    if not trajectory.rubric_provided:
        return {
            "available": False,
            "message": (
                "Where you stand against the rubric isn't available because no "
                "marking rubric was supplied for this task."
            ),
        }

    boundaries = tuple(trajectory.grade_boundaries_used)
    criteria = []
    for c in trajectory.criteria:
        estimated_grade = grade_for_percent(c.estimated_score_percent, boundaries) if boundaries else None
        criteria.append(
            {
                "code": c.criterion_code,
                "name": c.criterion_name,
                "estimated_grade": estimated_grade,
                "confidence": c.confidence,
                "rationale": c.rationale,
                "limitation": c.limitation,
            }
        )

    return {
        "available": True,
        "overall_estimated_grade": trajectory.estimated_grade,
        "overall_confidence": trajectory.overall_confidence,
        "biggest_opportunity": trajectory.biggest_opportunity,
        "next_boundary_requirements": trajectory.next_boundary_requirements,
        "criteria": criteria,
        "limitations": trajectory.limitations,
    }


def present_rubric_check(student_work_review: Optional[StudentWorkReview]) -> dict:
    """Tier 3: a concise per-criterion check -- current level, what's
    working, what's missing. Not a repeat of the whole rubric."""
    if student_work_review is None or not student_work_review.rubric_assessment:
        return {"available": False}
    return {
        "available": True,
        "criteria": [
            {
                "code": a.criterion_code,
                "name": a.criterion_name,
                "current_level": a.current_level,
                "whats_working": a.evidence,
                "whats_missing": a.gap_to_next_level,
            }
            for a in student_work_review.rubric_assessment
        ],
    }


def present_other_issues(
    student_work_review: Optional[StudentWorkReview],
    priority_issue_id: Optional[str],
) -> list[dict]:
    """Tier 4: everything else Stage 3 noticed, minus whichever issue
    already became the Tier 1 priority -- meant for a collapsed section,
    never the main event. Never exposes a raw issue id."""
    if student_work_review is None:
        return []
    return [
        {
            "category": _translate_category(issue.category),
            "observation": issue.observation,
            "why_it_matters": issue.why_it_matters,
        }
        for issue in student_work_review.issues
        if issue.id != priority_issue_id
    ]


def present_strengths(student_work_review: Optional[StudentWorkReview]) -> list[str]:
    """The specific strengths Stage 3 already found -- never generic praise
    invented here."""
    if student_work_review is None:
        return []
    return list(student_work_review.strengths)


# --- Screen D: "Toughest Teacher" ------------------------------------------------
#
# Translator for Stage 5 (Toughest Teacher Review). Never exposes a raw
# issue id, rank, or internal category string -- only the coaching language,
# the criteria it's tied to, and the genuine questions it leaves Ammu with.
# No AI calls happen here.

_PRIORITY_STATUS_LABELS = {
    "resolved": "You addressed the challenge",
    "partially_resolved": "You've made progress, but something still needs strengthening",
    "unresolved": "The main challenge is still there",
}


def present_toughest_teacher(review: Optional[ToughestTeacherReview]) -> dict:
    """Tiers 1 (verdict), 2 (still-unresolved challenges), 3 (what would
    change the teacher's mind), and 4 (the final challenge)."""
    if review is None:
        return {"available": False}

    had_previous_priority_to_check = review.priority_status is not None
    return {
        "available": True,
        "had_previous_priority_to_check": had_previous_priority_to_check,
        "verdict": _PRIORITY_STATUS_LABELS.get(review.priority_status) if review.priority_status else None,
        "priority_status_explanation": review.priority_status_explanation,
        "overall_judgment": review.overall_judgment,
        "trajectory_challenge": review.trajectory_challenge,
        "current_grade": review.current_grade,
        "unresolved_issues": [
            {
                "category": _translate_category(challenge.category),
                "related_criteria": [
                    {"code": ref.criterion_code, "name": ref.criterion_name}
                    for ref in challenge.related_criteria
                ],
                "observation": challenge.observation,
                "why_it_matters": challenge.why_it_matters,
                "teacher_challenge": challenge.teacher_challenge,
                "student_question": challenge.student_question,
            }
            for challenge in review.unresolved_issues
        ],
        "resolved_or_adequately_addressed": review.resolved_or_adequately_addressed,
        "what_would_change_my_mind": review.what_would_change_my_mind,
        "final_student_question": review.final_student_question,
        "final_improvement_target": review.final_improvement_target,
        "limitations": review.limitations,
    }


def present_revision_comparison(
    current_trajectory: Optional[RubricTrajectory],
    previous_trajectory: Optional[RubricTrajectory],
) -> dict:
    """A deterministic comparison between two drafts' already-computed
    trajectories -- never a new scoring system, just a diff of grades the
    engine already produced. Returns not-available when either side is
    missing, rather than guessing."""
    if current_trajectory is None or previous_trajectory is None:
        return {"available": False}

    previous_grade = previous_trajectory.estimated_grade
    current_grade = current_trajectory.estimated_grade
    trajectory_changed = None
    if previous_grade is not None and current_grade is not None:
        trajectory_changed = previous_grade != current_grade

    return {
        "available": True,
        "previous_grade": previous_grade,
        "current_grade": current_grade,
        "trajectory_changed": trajectory_changed,
    }
