"""Student-facing presentation/translation layer.

Pure functions: structured Stage 1/2 output in, plain dicts of Grade-9
friendly strings out. No AI calls happen here -- this is templating over
already-computed fields, not a new review capability. Keeping this separate
from any UI framework means the UI layer never touches a Stage 1-5 field
name directly (see the Student Experience design proposal, sections 8 and
16).

Only Stage 1 (Assignment Understanding) and Stage 2 (Rubric / Success
Criteria) are covered here -- that's what Screens A/B need. Translators for
Stage 3 / Rubric Trajectory / Stage 4 / Stage 5 are a Screen C/D concern,
not built yet.
"""

from __future__ import annotations

from ..assignment_understanding import AssignmentUnderstanding
from ..rubric_success_criteria import RubricCriterion, RubricSuccessCriteria


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
