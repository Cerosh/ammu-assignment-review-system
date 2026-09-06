"""Tests for the student-facing presentation/translation layer.

Pure functions, no model involved -- these just check the field mapping and
the honest "no rubric supplied" state are both correct.
"""

from __future__ import annotations

from ammu_review.app.presentation import (
    present_assignment_understanding,
    present_rubric_criterion,
    present_success_criteria,
)
from ammu_review.assignment_understanding import AssignmentUnderstanding
from ammu_review.rubric_success_criteria import RubricCriterion, RubricSuccessCriteria


def test_present_assignment_understanding_maps_fields():
    understanding = AssignmentUnderstanding(
        main_task="Explain the case and evaluate whether justice was served.",
        requirements=["Summarise the case"],
        assessed_skills=["5.3 Examines the role of law in society"],
        command_words=["Discuss: consider more than one side"],
        hidden_traps=["Don't just summarise"],
        top_band_thinking=["Links the outcome to the wider legal system"],
        checklist=["Have I named the relevant law?"],
    )

    presented = present_assignment_understanding(understanding)

    assert presented["what_youre_being_asked_to_do"] == understanding.main_task
    assert presented["requirements"] == understanding.requirements
    assert presented["checklist"] == understanding.checklist
    assert presented["watch_out_for"] == understanding.hidden_traps
    assert presented["key_words_to_notice"] == understanding.command_words
    # No raw field names or AI vocabulary should leak into the presented dict's keys.
    assert "assessed_skills" not in presented
    assert "top_band_thinking" not in presented


def test_present_rubric_criterion_maps_fields():
    criterion = RubricCriterion(
        code="5.3",
        name="Examines the role of law in society",
        teacher_wording="Analyses how the law responds to social issues.",
        student_friendly_meaning="Show how the law reacted to this situation.",
        observable_evidence=["Names the relevant law."],
        top_band_requirements=["Links the outcome to a broader effect."],
        good_vs_outstanding="Outstanding responses justify the link with evidence.",
        common_failure_modes=["Naming the law without explaining its effect."],
    )

    presented = present_rubric_criterion(criterion)

    assert presented["code"] == "5.3"
    assert presented["name"] == criterion.name
    assert presented["what_it_means"] == criterion.student_friendly_meaning
    assert presented["what_top_marks_need"] == criterion.top_band_requirements
    assert presented["good_vs_outstanding"] == criterion.good_vs_outstanding
    assert presented["common_mistakes"] == criterion.common_failure_modes


def test_present_success_criteria_with_rubric():
    success_criteria = RubricSuccessCriteria(
        rubric_provided=True,
        criteria=[
            RubricCriterion(
                code="5.3",
                name="Examines the role of law in society",
                teacher_wording="Analyses how the law responds to social issues.",
                student_friendly_meaning="Show how the law reacted to this situation.",
                observable_evidence=["Names the relevant law."],
                top_band_requirements=["Links the outcome to a broader effect."],
                good_vs_outstanding="Outstanding responses justify the link with evidence.",
                common_failure_modes=["Naming the law without explaining its effect."],
            )
        ],
        overall_top_band_profile="Links the case to the broader legal system.",
        success_checklist=["Does my work link the outcome to a broader effect?"],
        limitations=[],
    )

    presented = present_success_criteria(success_criteria)

    assert presented["rubric_provided"] is True
    assert presented["overview"] == success_criteria.overall_top_band_profile
    assert len(presented["criteria"]) == 1
    assert presented["criteria"][0]["code"] == "5.3"
    assert presented["checklist"] == success_criteria.success_checklist


def test_present_success_criteria_without_rubric_is_honest_not_silent():
    success_criteria = RubricSuccessCriteria(
        rubric_provided=False,
        criteria=[],
        overall_top_band_profile="",
        success_checklist=["Have I addressed the task as fully as I can?"],
        limitations=["No marking rubric was supplied."],
    )

    presented = present_success_criteria(success_criteria)

    assert presented["rubric_provided"] is False
    assert presented["criteria"] == []
    assert "No marking rubric was given" in presented["message"]
    assert presented["checklist"] == success_criteria.success_checklist
