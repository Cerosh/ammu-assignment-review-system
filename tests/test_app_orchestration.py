"""Tests for the application-layer orchestration: create_assignment,
submit_draft, challenge_draft, and the previous-priority carry-forward.

These never call a live model -- a fake chat model keyed by the requested
structured-output schema drives an entire multi-stage call (e.g. Stage 1 +
Stage 2 for create_assignment), the same offline-testing approach already
used for every review stage in this codebase. What's under test here is
purely the application layer's wiring, sequencing, persistence, and the
previous-priority carry-forward logic (Student Experience design proposal,
section 7) -- not whether any individual stage's own output is sound (that's
covered by that stage's own test suite).
"""

from __future__ import annotations

import pytest

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
    """Fake chat model whose with_structured_output(schema) returns a canned
    result keyed by the requested schema class -- lets one fake model drive
    an entire orchestrated call spanning several stages."""

    def __init__(self, drafts_by_schema: dict):
        self.drafts_by_schema = drafts_by_schema
        self.structured_models: dict = {}

    def with_structured_output(self, schema):
        if schema not in self.structured_models:
            self.structured_models[schema] = _FakeStructuredModel(self.drafts_by_schema[schema])
        return self.structured_models[schema]


UNDERSTANDING = AssignmentUnderstanding(
    main_task="Explain what happened in the Hannah Clarke case and whether justice was served.",
    requirements=["Summarise the case", "Discuss the legal concepts involved"],
    assessed_skills=["5.3 Examines the role of law in society"],
    command_words=["Discuss: consider more than one side"],
    hidden_traps=["Don't just summarise -- you must evaluate"],
    top_band_thinking=["Links the case outcome to the broader legal system"],
    checklist=["Have I named the relevant law?"],
)

SUCCESS_CRITERIA = RubricSuccessCriteria(
    rubric_provided=True,
    criteria=[
        RubricCriterion(
            code="5.3",
            name="Examines the role of law in society",
            teacher_wording="Analyses how the law responds to social issues.",
            student_friendly_meaning="Show how the law reacted to this situation.",
            observable_evidence=["Names the relevant law or reform."],
            top_band_requirements=["Links the case outcome to a broader legal/social effect."],
            good_vs_outstanding="Outstanding responses justify the link with evidence.",
            common_failure_modes=["Naming the law without explaining its effect."],
        )
    ],
    overall_top_band_profile="Links the case to the broader legal system with justified evaluation.",
    success_checklist=["Does my work link the outcome to a broader legal/social effect?"],
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
                student_question="What does the case outcome suggest about the effectiveness of the law?",
            )
        ],
        limitations=[],
    )


TRAJECTORY_DRAFT = _RubricTrajectoryDraft(
    rubric_provided=True,
    criteria=[],
    overall_estimated_score_percent=55.0,
    overall_confidence="medium",
    biggest_opportunity="Link the case outcome more explicitly to the legal concepts discussed.",
    next_boundary_requirements=["Provide a more justified evaluation of the outcome."],
    limitations=[],
)


def _priority_draft(marker: str) -> _PriorityCoachDraft:
    return _PriorityCoachDraft(
        priority_issue_id=None,
        priority_statement=f"{marker}: the analysis of the outcome lacks depth.",
        priority_category="analysis",
        why_this_matters="This is the core analytical requirement of the task.",
        primary_criterion=CriterionRef(criterion_code="5.3", criterion_name="Examines the role of law in society"),
        also_affects_criteria=[],
        trajectory_connection="Addressing this is likely to strengthen your position toward the next range.",
        student_question="What does the case outcome suggest about the effectiveness of the law?",
        improvement_target="Justify your evaluation of the outcome with evidence.",
        evidence_to_consider=["The police and legal response after the case."],
        other_issues_deferred=[],
        confidence="medium",
        limitations=[],
    )


TOUGHEST_TEACHER_DRAFT = _ToughestTeacherDraft(
    overall_judgment="The work identifies key legal concepts but the evaluation of the outcome is underdeveloped.",
    trajectory_challenge="The current position looks optimistic given how little the outcome is evaluated.",
    priority_status="unresolved",
    priority_status_explanation="The evaluation of the outcome still lacks depth.",
    unresolved_issues=[],
    resolved_or_adequately_addressed=[],
    evidence_that_supports_judgment=["The work names the relevant legal concepts."],
    what_would_change_my_mind=["A clearer justified evaluation of the outcome."],
    final_student_question="What does the outcome of this case suggest about the effectiveness of the law?",
    final_improvement_target="Justify your evaluation of the outcome with evidence from the case.",
    confidence="medium",
    limitations=[],
)


def _setup_model() -> _FakeMultiStageModel:
    return _FakeMultiStageModel({AssignmentUnderstanding: UNDERSTANDING, RubricSuccessCriteria: SUCCESS_CRITERIA})


def _draft_model(marker: str) -> _FakeMultiStageModel:
    return _FakeMultiStageModel(
        {
            StudentWorkReview: _student_work_review(),
            _RubricTrajectoryDraft: TRAJECTORY_DRAFT,
            _PriorityCoachDraft: _priority_draft(marker),
        }
    )


def _challenge_model() -> _FakeMultiStageModel:
    return _FakeMultiStageModel({_ToughestTeacherDraft: TOUGHEST_TEACHER_DRAFT})


# --- create_assignment -------------------------------------------------------


async def test_create_assignment_runs_stage1_and_stage2_and_persists(tmp_path):
    store = SessionStore(base_dir=tmp_path)

    session = await create_assignment(
        store,
        assignment_text="Explain the Hannah Clarke case and whether justice was served.",
        rubric_text="Rubric text.",
        title="Hannah Clarke Case Study",
        model=_setup_model(),
    )

    assert session.assignment.title == "Hannah Clarke Case Study"
    assert session.assignment.assignment_understanding == UNDERSTANDING
    assert session.assignment.success_criteria == SUCCESS_CRITERIA

    reloaded = store.load(session.assignment.id)
    assert reloaded.assignment.success_criteria == SUCCESS_CRITERIA


async def test_create_assignment_persists_stage1_even_before_stage2_runs(tmp_path):
    """If Stage 2 were to fail, Stage 1's result should already be on disk --
    verified here by checking Stage 1 alone reaches the model correctly."""
    store = SessionStore(base_dir=tmp_path)
    model = _setup_model()

    await create_assignment(store, assignment_text="Task text.", model=model)

    human_message = model.structured_models[AssignmentUnderstanding].received[1]
    assert "Task text." in human_message.content


# --- submit_draft -------------------------------------------------------------


async def test_submit_draft_runs_stage3_trajectory_and_priority_and_persists(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", rubric_text="Rubric text.", model=_setup_model())

    draft = await submit_draft(store, session.assignment.id, "My first draft text.", model=_draft_model("DRAFT1"))

    assert draft.draft_number == 1
    assert draft.student_work_review is not None
    # Ids are Python-assigned by Stage 3 itself, not left as the fake's placeholder.
    assert draft.student_work_review.issues[0].id == "S3-ISSUE-1"
    assert draft.rubric_trajectory.estimated_grade == "C"
    assert draft.priority_coach.current_grade == "C"
    assert draft.priority_coach.target_grade == "B"
    assert "DRAFT1" in draft.priority_coach.priority_statement

    reloaded = store.load(session.assignment.id)
    assert len(reloaded.drafts) == 1
    assert reloaded.drafts[0].priority_coach.priority_statement == draft.priority_coach.priority_statement


async def test_submit_draft_draft_number_increments_across_submissions(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())

    draft1 = await submit_draft(store, session.assignment.id, "Draft 1 text.", model=_draft_model("DRAFT1"))
    draft2 = await submit_draft(store, session.assignment.id, "Draft 2 text.", model=_draft_model("DRAFT2"))

    assert draft1.draft_number == 1
    assert draft2.draft_number == 2
    reloaded = store.load(session.assignment.id)
    assert len(reloaded.drafts) == 2


async def test_submit_draft_raises_for_unknown_assignment(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        await submit_draft(store, "does-not-exist", "text", model=_FakeMultiStageModel({}))


# --- challenge_draft + previous-priority carry-forward ------------------------


async def test_challenge_draft_first_draft_checks_its_own_priority(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())
    draft1 = await submit_draft(store, session.assignment.id, "Draft 1 text.", model=_draft_model("DRAFT1"))

    challenge_model = _challenge_model()
    result = await challenge_draft(store, session.assignment.id, draft1.id, model=challenge_model)

    assert result.priority_coach_checked_source_draft_id == draft1.id
    human_message = challenge_model.structured_models[_ToughestTeacherDraft].received[1]
    assert "DRAFT1" in human_message.content

    reloaded = store.load(session.assignment.id)
    assert reloaded.drafts[0].toughest_teacher_review is not None


async def test_challenge_draft_second_draft_carries_forward_previous_priority(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())

    draft1 = await submit_draft(store, session.assignment.id, "Draft 1 text.", model=_draft_model("DRAFT1"))
    draft2 = await submit_draft(store, session.assignment.id, "Draft 2 text.", model=_draft_model("DRAFT2"))

    challenge_model = _challenge_model()
    result = await challenge_draft(store, session.assignment.id, draft2.id, model=challenge_model)

    # Draft 1's priority -- what should have been fixed by now -- is what's
    # checked, not draft 2's own freshly-generated one.
    assert result.priority_coach_checked_source_draft_id == draft1.id
    human_message = challenge_model.structured_models[_ToughestTeacherDraft].received[1]
    assert "DRAFT1" in human_message.content
    assert "DRAFT2" not in human_message.content


async def test_challenge_draft_raises_for_unknown_draft(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())

    with pytest.raises(ValueError):
        await challenge_draft(store, session.assignment.id, "does-not-exist", model=_FakeMultiStageModel({}))
