"""Phase D: revision lineage and previous-priority carry-forward.

Most of this behaviour was already built (and already tested) in Phase A's
submit_draft()/challenge_draft() -- see test_app_orchestration.py:
- first draft preserved / a revision gets a new draft id, linked to the
  assignment (test_submit_draft_draft_number_increments_across_submissions)
- a revision receives a fresh Stage 3 / Rubric Trajectory / Priority Coach
  review, never reused (test_submit_draft_runs_stage3_trajectory_and_priority_and_persists)
- the previous draft's priority is carried into Stage 5
  (test_challenge_draft_second_draft_carries_forward_previous_priority)

This file closes the one gap Phase D's checklist calls out that wasn't
already covered: what happens when the previous draft exists but its own
PriorityCoach never identified a specific issue (priority_issue_id is
None) -- Stage 5 must be called with that as-is, never a fabricated
priority, and must not crash. It also locks in that there is exactly one
place this carry-forward decision is made (no parallel algorithm).

Fixtures are duplicated rather than imported from test_app_orchestration.py
-- tests/ has no __init__.py, so cross-file imports aren't part of this
codebase's convention; every existing test file is self-contained.
"""

from __future__ import annotations

import inspect

from ammu_review.app import orchestration
from ammu_review.app.orchestration import challenge_draft, create_assignment, submit_draft
from ammu_review.app.store import SessionStore
from ammu_review.assignment_understanding import AssignmentUnderstanding
from ammu_review.priority_coach import CriterionRef, _PriorityCoachDraft
from ammu_review.rubric_success_criteria import RubricCriterion, RubricSuccessCriteria
from ammu_review.student_work_review import (
    AnalysisReview,
    DimensionReview,
    ReviewIssue,
    StudentWorkReview,
    _RubricTrajectoryDraft,
)
from ammu_review.toughest_teacher import _ToughestTeacherDraft


class _FakeStructuredModel:
    def __init__(self, result):
        self.result = result
        self.received = None

    async def ainvoke(self, messages, *args, **kwargs):
        self.received = messages
        return self.result.model_copy(deep=True)


class _FakeMultiStageModel:
    def __init__(self, drafts_by_schema: dict):
        self.drafts_by_schema = drafts_by_schema
        self.structured_models: dict = {}

    def with_structured_output(self, schema):
        if schema not in self.structured_models:
            self.structured_models[schema] = _FakeStructuredModel(self.drafts_by_schema[schema])
        return self.structured_models[schema]


UNDERSTANDING = AssignmentUnderstanding(
    main_task="Explain the Hannah Clarke case and whether justice was served.",
    requirements=["Summarise the case"],
    assessed_skills=["5.3 Examines the role of law in society"],
    command_words=["Discuss"],
    hidden_traps=[],
    top_band_thinking=[],
    checklist=[],
)

SUCCESS_CRITERIA = RubricSuccessCriteria(
    rubric_provided=True,
    criteria=[
        RubricCriterion(
            code="5.3",
            name="Examines the role of law in society",
            teacher_wording="Analyses how the law responds to social issues.",
            student_friendly_meaning="Show how the law reacted to this situation.",
            observable_evidence=[],
            top_band_requirements=[],
            good_vs_outstanding="Outstanding responses justify the link with evidence.",
            common_failure_modes=[],
        )
    ],
    overall_top_band_profile="Links the case to the broader legal system.",
    success_checklist=[],
    limitations=[],
)


def _dimension(status: str = "partial") -> DimensionReview:
    return DimensionReview(status=status, observation="Some observation.")


def _student_work_review() -> StudentWorkReview:
    return StudentWorkReview(
        strengths=["Clear narrative of events."],
        task_alignment="Addresses most requirements.",
        rubric_assessment=[],
        evidence_reviews=[],
        analysis_review=AnalysisReview(
            what=_dimension("strong"), how=_dimension("partial"), why=_dimension("missing"), so_what=_dimension("missing")
        ),
        issues=[
            ReviewIssue(
                id="PLACEHOLDER",
                category="analysis",
                severity="high",
                location="Final paragraph.",
                observation="The analysis of the outcome lacks depth.",
                why_it_matters="This is the core analytical requirement of the task.",
                student_question="What does the outcome suggest about the effectiveness of the law?",
            )
        ],
        limitations=[],
    )


TRAJECTORY_DRAFT = _RubricTrajectoryDraft(
    rubric_provided=True,
    criteria=[],
    overall_estimated_score_percent=55.0,
    overall_confidence="medium",
    biggest_opportunity="Link the outcome to the wider legal system.",
    next_boundary_requirements=[],
    limitations=[],
)


def _priority_draft_with_no_issue() -> _PriorityCoachDraft:
    """A PriorityCoach draft where Stage 4 didn't tie its priority to any
    specific Stage 3 issue -- priority_issue_id is None."""
    return _PriorityCoachDraft(
        priority_issue_id=None,
        priority_statement="Keep developing your evaluation of the outcome.",
        priority_category="analysis",
        why_this_matters="This is the core analytical requirement of the task.",
        primary_criterion=CriterionRef(criterion_code="5.3", criterion_name="Examines the role of law in society"),
        also_affects_criteria=[],
        trajectory_connection="Addressing this is likely to strengthen your position.",
        student_question="What does the outcome suggest about the effectiveness of the law?",
        improvement_target="Justify your evaluation with evidence.",
        evidence_to_consider=[],
        other_issues_deferred=[],
        confidence="medium",
        limitations=[],
    )


def _toughest_teacher_draft() -> _ToughestTeacherDraft:
    return _ToughestTeacherDraft(
        overall_judgment="Reasonable attempt.",
        trajectory_challenge="No firm trajectory yet.",
        priority_status=None,
        priority_status_explanation="No specific priority was supplied to check.",
        unresolved_issues=[],
        resolved_or_adequately_addressed=[],
        evidence_that_supports_judgment=[],
        what_would_change_my_mind=["A clearer analysis of the outcome."],
        final_student_question="What would make your evaluation more convincing?",
        final_improvement_target="Justify your evaluation with evidence.",
        confidence="medium",
        limitations=[],
    )


def _setup_model() -> _FakeMultiStageModel:
    return _FakeMultiStageModel({AssignmentUnderstanding: UNDERSTANDING, RubricSuccessCriteria: SUCCESS_CRITERIA})


def _draft_model_with_no_priority() -> _FakeMultiStageModel:
    return _FakeMultiStageModel(
        {
            StudentWorkReview: _student_work_review(),
            _RubricTrajectoryDraft: TRAJECTORY_DRAFT,
            _PriorityCoachDraft: _priority_draft_with_no_issue(),
        }
    )


async def test_first_draft_with_no_priority_checks_its_own_none_priority_without_crashing(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())

    draft1 = await submit_draft(store, session.assignment.id, "Draft 1 text.", model=_draft_model_with_no_priority())
    assert draft1.priority_coach.priority_issue_id is None

    challenge_model = _FakeMultiStageModel({_ToughestTeacherDraft: _toughest_teacher_draft()})
    updated = await challenge_draft(store, session.assignment.id, draft1.id, model=challenge_model)

    assert updated.priority_coach_checked_source_draft_id == draft1.id


async def test_previous_draft_with_no_priority_coach_passes_none_not_a_fabricated_priority(tmp_path):
    """Item 8: the previous draft exists, but its own PriorityCoach never
    identified a specific issue -- Stage 5 must receive that faithfully
    (no invented issue reference), and the app must not crash."""
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())

    draft1 = await submit_draft(store, session.assignment.id, "Draft 1 text.", model=_draft_model_with_no_priority())
    draft2 = await submit_draft(store, session.assignment.id, "Draft 2 text.", model=_draft_model_with_no_priority())

    challenge_model = _FakeMultiStageModel({_ToughestTeacherDraft: _toughest_teacher_draft()})
    updated = await challenge_draft(store, session.assignment.id, draft2.id, model=challenge_model)

    # The real object carried forward is draft 1's PriorityCoach -- itself
    # carrying no specific issue reference.
    assert updated.priority_coach_checked_source_draft_id == draft1.id
    human_message = challenge_model.structured_models[_ToughestTeacherDraft].received[1]
    assert "priority_issue_id\": null" in human_message.content


def test_resolve_priority_coach_for_challenge_is_the_single_source_of_truth():
    """There is exactly one place this carry-forward decision is made -- no
    parallel resolution algorithm exists elsewhere in the application
    layer."""
    source = inspect.getsource(orchestration)
    assert source.count("def _resolve_priority_coach_for_challenge") == 1
    assert source.count("_resolve_priority_coach_for_challenge(") == 2  # the def, plus its one call site
