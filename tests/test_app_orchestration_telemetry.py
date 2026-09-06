"""Tests that ammu_review.app.orchestration emits the expected telemetry
events (and only those), that a telemetry failure never breaks the actual
review, and that no raw student text ever reaches an event.

Reuses the same fake-model-keyed-by-schema approach as
test_app_orchestration.py for driving the stage calls themselves -- what's
under test here is telemetry integration, not stage wiring (already covered
there).
"""

from __future__ import annotations

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
from ammu_review.telemetry.models import EventType
from ammu_review.telemetry.recorder import TelemetryRecorder
from ammu_review.telemetry.store import TelemetryStore
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
    hidden_traps=["Don't just summarise"],
    top_band_thinking=["Links the outcome to the wider legal system"],
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
    biggest_opportunity="Link the outcome more explicitly to the legal concepts discussed.",
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
        trajectory_connection="Addressing this is likely to strengthen your position.",
        student_question="What does the outcome suggest about the effectiveness of the law?",
        improvement_target="Justify your evaluation of the outcome with evidence.",
        evidence_to_consider=["The police and legal response after the case."],
        other_issues_deferred=[],
        confidence="medium",
        limitations=[],
    )


TOUGHEST_TEACHER_DRAFT = _ToughestTeacherDraft(
    overall_judgment="The work names the legal concepts but the evaluation of the outcome is underdeveloped.",
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


class _CapturingRecorder:
    """A fake TelemetryRecorder that just remembers what it was asked to
    record, so tests can assert exact event sequences/metadata without
    touching disk."""

    def __init__(self):
        self.events: list[dict] = []

    def record(self, event_type, assignment_id, draft_id=None, metadata=None, session_id=None):
        self.events.append(
            {
                "event_type": event_type,
                "assignment_id": assignment_id,
                "draft_id": draft_id,
                "metadata": metadata or {},
                "session_id": session_id or assignment_id,
            }
        )


# --- create_assignment --------------------------------------------------------


async def test_create_assignment_emits_created_then_understood(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    recorder = _CapturingRecorder()

    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model(), recorder=recorder)

    assert [e["event_type"] for e in recorder.events] == [
        EventType.ASSIGNMENT_CREATED,
        EventType.ASSIGNMENT_UNDERSTOOD,
    ]
    assert all(e["assignment_id"] == session.assignment.id for e in recorder.events)
    assert recorder.events[1]["metadata"] == {"rubric_provided": True}


# --- submit_draft ---------------------------------------------------------------


async def test_submit_draft_first_draft_emits_expected_sequence(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())

    recorder = _CapturingRecorder()
    draft = await submit_draft(
        store, session.assignment.id, "My first draft text.", model=_draft_model("DRAFT1"), recorder=recorder
    )

    assert [e["event_type"] for e in recorder.events] == [
        EventType.DRAFT_SUBMITTED,
        EventType.REVIEW_STARTED,
        EventType.REVIEW_COMPLETED,
        EventType.PRIORITY_SELECTED,
    ]
    assert all(e["draft_id"] == draft.id for e in recorder.events)

    submitted_meta = recorder.events[0]["metadata"]
    assert submitted_meta["draft_number"] == 1
    assert submitted_meta["word_count"] == len("My first draft text.".split())

    completed_meta = recorder.events[2]["metadata"]
    assert completed_meta["success"] is True
    assert completed_meta["issue_count"] == 1
    assert completed_meta["model_call_count"] == 3
    assert isinstance(completed_meta["duration_ms"], int)

    selected_meta = recorder.events[3]["metadata"]
    assert selected_meta["priority_category"] == "analysis"
    assert selected_meta["criterion_code"] == "5.3"
    assert selected_meta["current_grade"] == "C"
    assert selected_meta["target_grade"] == "B"


async def test_submit_draft_second_draft_also_emits_revision_submitted(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())
    draft1 = await submit_draft(store, session.assignment.id, "Draft 1 text.", model=_draft_model("DRAFT1"))

    recorder = _CapturingRecorder()
    draft2 = await submit_draft(
        store, session.assignment.id, "Draft 2 text.", model=_draft_model("DRAFT2"), recorder=recorder
    )

    assert [e["event_type"] for e in recorder.events] == [
        EventType.DRAFT_SUBMITTED,
        EventType.REVISION_SUBMITTED,
        EventType.REVIEW_STARTED,
        EventType.REVIEW_COMPLETED,
        EventType.PRIORITY_SELECTED,
    ]
    revision_meta = recorder.events[1]["metadata"]
    assert revision_meta == {"previous_draft_id": draft1.id, "new_draft_id": draft2.id, "draft_number": 2}


async def test_submit_draft_failure_emits_review_completed_with_success_false(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())

    class _RaisingModel:
        def with_structured_output(self, schema):
            raise RuntimeError("simulated model failure")

    recorder = _CapturingRecorder()
    try:
        await submit_draft(store, session.assignment.id, "Draft 1 text.", model=_RaisingModel(), recorder=recorder)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected the simulated model failure to propagate")

    assert [e["event_type"] for e in recorder.events] == [
        EventType.DRAFT_SUBMITTED,
        EventType.REVIEW_STARTED,
        EventType.REVIEW_COMPLETED,
    ]
    completed_meta = recorder.events[2]["metadata"]
    assert completed_meta["success"] is False
    assert completed_meta["error_type"] == "RuntimeError"


# --- challenge_draft --------------------------------------------------------------


async def test_challenge_draft_emits_started_then_completed(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())
    draft1 = await submit_draft(store, session.assignment.id, "Draft 1 text.", model=_draft_model("DRAFT1"))
    draft2 = await submit_draft(store, session.assignment.id, "Draft 2 text.", model=_draft_model("DRAFT2"))

    recorder = _CapturingRecorder()
    await challenge_draft(store, session.assignment.id, draft2.id, model=_challenge_model(), recorder=recorder)

    assert [e["event_type"] for e in recorder.events] == [
        EventType.PRIORITY_CHALLENGE_STARTED,
        EventType.PRIORITY_CHALLENGE_COMPLETED,
    ]
    assert recorder.events[0]["metadata"] == {"priority_coach_source_draft_id": draft1.id}

    completed_meta = recorder.events[1]["metadata"]
    assert completed_meta["success"] is True
    assert completed_meta["previous_priority_issue_id"] is None
    assert completed_meta["priority_status"] == "unresolved"
    # Both drafts share the same fixture trajectory (55% -> "C") -> unchanged.
    assert completed_meta["trajectory_changed"] is False


async def test_challenge_draft_first_draft_has_no_trajectory_changed_signal(tmp_path):
    """Nothing earlier to compare against -- trajectory_changed stays None,
    never a fabricated True/False."""
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())
    draft1 = await submit_draft(store, session.assignment.id, "Draft 1 text.", model=_draft_model("DRAFT1"))

    recorder = _CapturingRecorder()
    await challenge_draft(store, session.assignment.id, draft1.id, model=_challenge_model(), recorder=recorder)

    assert recorder.events[1]["metadata"]["trajectory_changed"] is None


# --- failure isolation + privacy --------------------------------------------------


async def test_telemetry_failure_does_not_break_submit_draft(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())

    class _BrokenStore:
        def append(self, event):
            raise OSError("simulated telemetry storage failure")

    broken_recorder = TelemetryRecorder(store=_BrokenStore())

    draft = await submit_draft(
        store, session.assignment.id, "Draft 1 text.", model=_draft_model("DRAFT1"), recorder=broken_recorder
    )

    assert draft.priority_coach is not None
    assert "DRAFT1" in draft.priority_coach.priority_statement


async def test_unusable_telemetry_directory_does_not_break_submit_draft(tmp_path, monkeypatch):
    """A step earlier than test_telemetry_failure_does_not_break_submit_draft
    above: here nothing injects a recorder at all, so submit_draft's own
    `recorder or TelemetryRecorder()` default is what's exercised -- the
    exact path that used to crash when TelemetryStore()'s directory
    creation failed, since that happened outside any try/except."""
    store = SessionStore(base_dir=tmp_path / "sessions")
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())

    blocking_file = tmp_path / "not_a_directory"
    blocking_file.write_text("this is a file, not a directory")
    monkeypatch.setenv("AMMU_TELEMETRY_DIR", str(blocking_file / "telemetry"))

    draft = await submit_draft(store, session.assignment.id, "Draft 1 text.", model=_draft_model("DRAFT1"))

    assert draft.priority_coach is not None
    assert "DRAFT1" in draft.priority_coach.priority_statement


async def test_no_raw_student_work_text_appears_in_any_event(tmp_path):
    store = SessionStore(base_dir=tmp_path)
    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model())

    recorder = _CapturingRecorder()
    marker = "UNIQUE-STUDENT-SENTENCE-MARKER-12345"
    await submit_draft(
        store, session.assignment.id, f"{marker} rest of my draft.", model=_draft_model("DRAFT1"), recorder=recorder
    )

    assert marker not in str(recorder.events)


# --- real end-to-end persistence ---------------------------------------------------


async def test_real_telemetry_store_receives_events_from_orchestration(tmp_path):
    store = SessionStore(base_dir=tmp_path / "sessions")
    recorder = TelemetryRecorder(store=TelemetryStore(base_dir=tmp_path / "telemetry"))

    session = await create_assignment(store, assignment_text="Task text.", model=_setup_model(), recorder=recorder)
    await submit_draft(store, session.assignment.id, "Draft 1 text.", model=_draft_model("DRAFT1"), recorder=recorder)

    events = recorder.store.read_events(session.assignment.id)
    assert [e.event_type for e in events] == [
        EventType.ASSIGNMENT_CREATED,
        EventType.ASSIGNMENT_UNDERSTOOD,
        EventType.DRAFT_SUBMITTED,
        EventType.REVIEW_STARTED,
        EventType.REVIEW_COMPLETED,
        EventType.PRIORITY_SELECTED,
    ]
