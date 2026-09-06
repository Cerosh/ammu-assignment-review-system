"""Stage 5: Toughest Teacher Review.

Stage 3 is the broad diagnostic reviewer. Stage 4 picks one coaching
priority. Stage 5 is the final adversarial check: "if I were the toughest
reasonable teacher marking this against this rubric, what would I still
challenge before letting this work move into the next grade band?" It is
not another full review -- it re-examines Stage 4's specific priority (has
it actually been addressed?), challenges whether Rubric Trajectory's
current position is justified (without inventing a new percentage), and
surfaces a small, ranked set of the most significant remaining challenges.

This is the final planned review stage. After this, the review engine is
considered feature-complete -- no more stages, no revision loop yet.

This is a fully additive, new stage -- it does not modify Stage 1, Stage 2,
Stage 3, Rubric Trajectory, or Stage 4. It only *consumes* their results as
either source material (assignment/rubric/student work) or AI-generated
context (Stage 1-4 results, explicitly not authoritative -- the rubric
remains the sole authority).

The prompt that defines this role lives in ``prompts/05_toughest_teacher.md``,
kept separate from this module so the instructions can be edited without
touching code.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from .assignment_understanding import AssignmentUnderstanding
from .config import get_model
from .priority_coach import CriterionRef, PriorityCoach
from .rubric_success_criteria import RubricSuccessCriteria
from .student_work_review import RubricTrajectory, StudentWorkReview

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "05_toughest_teacher.md"
SYSTEM_PROMPT_TEXT = PROMPT_PATH.read_text()

_NOT_PROVIDED = "Not provided."
_NO_TRAJECTORY = "Not available -- no Rubric Trajectory context was supplied."
_NO_PRIORITY = "Not available -- no Stage 4 Priority Coach context was supplied."

_PERCENT_PATTERN = re.compile(r"\d+(\.\d+)?\s*%")

_HUMAN_TEMPLATE = """# SOURCE MATERIAL (authoritative)

## Assignment / Task Sheet

{assignment}

## Marking Criteria / Rubric

{rubric}

## Additional Teacher Instructions

{teacher_instructions}

## Ammu's Submitted Work

{student_work}

# AI-GENERATED CONTEXT (not authoritative -- the rubric above remains authoritative)

## Stage 1 Assignment Understanding

{assignment_understanding}

## Stage 2 Rubric Success Criteria

{success_criteria}

## Stage 3 Student Work Review

{student_work_review}

## Rubric Trajectory

{rubric_trajectory}

## Stage 4 Priority Coach

{priority_coach}

## Already-computed context (do not recompute or second-guess this)

Current estimated position (from Rubric Trajectory): {current_grade}
Stage 4's selected priority issue id (check whether THIS specific issue has been resolved): {priority_coach_issue_id}

Perform the final adversarial review following your role and produce the structured output."""


class TeacherChallenge(BaseModel):
    """One significant remaining challenge -- NOT a full re-review, only the
    handful genuinely worth the toughest teacher's attention."""

    rank: int = Field(
        description="1 = the single most important remaining challenge. Used to identify the "
        "strongest challenge without relying on list order alone."
    )
    issue_id: Optional[str] = Field(
        default=None,
        description="References a Stage 3 issue id if this challenge corresponds to one. "
        "Validated in Python after generation -- an id that doesn't match a real supplied issue "
        "will be discarded, not trusted.",
    )
    category: Literal["content", "evidence", "analysis", "accuracy", "structure", "grammar", "rubric"] = Field(
        description="Same categories as Stage 3's issue categories. If issue_id resolves to a "
        "real Stage 3 issue, this is overwritten in Python from that issue's actual category."
    )
    related_criteria: list[CriterionRef] = Field(
        default_factory=list, description="Rubric criteria this challenge relates to."
    )
    observation: str = Field(
        description="What's actually there in her work. 1-3 sentences, concise -- not a paragraph."
    )
    why_it_matters: str = Field(
        description="Why this matters, tied to the task/rubric -- not generic writing advice. "
        "1-2 sentences."
    )
    teacher_challenge: str = Field(
        description="The actual adversarial pushback -- what a demanding but fair teacher would "
        "say before accepting this as sufficient. Never a rewritten sentence or replacement "
        "text. 1-3 sentences, concise."
    )
    student_question: str = Field(
        description="A genuine question tied to this specific challenge. Must end with '?', "
        "must not contain or imply the answer, must not be a disguised instruction to write or "
        "copy a particular sentence."
    )


class _ToughestTeacherDraft(BaseModel):
    """What the model produces. ``current_grade``/``priority_coach_issue_id``
    are NOT here -- they're echoed in Python from the supplied upstream
    results before the model is even called, never asked of the model."""

    overall_judgment: str = Field(
        description="A fair, holistic verdict. If the work is genuinely strong, say so plainly "
        "-- do not manufacture criticism to sound rigorous. 2-4 sentences, concise -- not an "
        "essay."
    )
    trajectory_challenge: str = Field(
        description="Whether the current estimated position (grade letter given to you) is "
        "actually justified by the evidence in the work, and why -- or why it looks solid. "
        "NEVER state a new percentage or grade; only challenge or affirm the existing one, in "
        "qualitative terms. If no Rubric Trajectory context was supplied (the 'Current "
        "estimated position' given to you says 'Not available'), this field must be EXACTLY, "
        "verbatim: 'Trajectory framing is not available because no Rubric Trajectory context "
        "was supplied.' Otherwise, 1-2 sentences, concise."
    )
    priority_status: Optional[Literal["resolved", "partially_resolved", "unresolved"]] = Field(
        default=None,
        description="Whether Stage 4's selected priority (if supplied) has been addressed in "
        "the CURRENT submitted work. Unset if no Stage 4 priority was supplied -- do not invent "
        "one to check.",
    )
    priority_status_explanation: str = Field(
        description="Why -- grounded in the actual current work. If no Stage 4 priority was "
        "supplied, state that plainly here instead. 1-2 sentences."
    )
    unresolved_issues: list[TeacherChallenge] = Field(
        default_factory=list,
        description="The most significant remaining challenges only -- AT MOST 3 entries, even "
        "if more could be listed. NOT a full re-review of Stage 3's list. Empty if the work is "
        "genuinely strong enough that no significant challenge remains.",
    )
    resolved_or_adequately_addressed: list[str] = Field(
        default_factory=list,
        description="Things Stage 3 or Stage 4 flagged that are now resolved or already "
        "adequately addressed in the current work -- acknowledge progress, do not keep "
        "attacking these.",
    )
    evidence_that_supports_judgment: list[str] = Field(
        default_factory=list,
        description="Specific things from her actual work that ground overall_judgment -- not "
        "generic.",
    )
    what_would_change_my_mind: list[str] = Field(
        default_factory=list,
        description="What specific change or evidence in a revision would change this verdict "
        "-- described as a target to reach, never as content to insert.",
    )
    final_student_question: str = Field(
        description="THE single most demanding question for Ammu, tied to the strongest "
        "remaining challenge. Must end with '?'. Must NOT contain or imply the answer, and must "
        "NOT be a disguised instruction to write or copy a particular sentence."
    )
    final_improvement_target: str = Field(
        description="Describes the quality of thinking/evidence a successful response to the "
        "final challenge would demonstrate -- never the actual content of the answer. 1-3 "
        "sentences, concise."
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence in this overall judgement -- lower if the supplied work is "
        "thin, or upstream context (rubric, Stage 3/4) was missing or limited."
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Explicit statements of what could not be determined -- e.g. no rubric was "
        "supplied, no Stage 3/4/Trajectory context was supplied, or the work is too short to "
        "judge whether a specific issue was resolved. Never fill these gaps with generic "
        "assumptions.",
    )


class ToughestTeacherReview(_ToughestTeacherDraft):
    """Public result: the model's draft plus deterministic context/validation
    applied in Python -- never invented by the model."""

    current_grade: Optional[str] = Field(
        default=None,
        description="Echoed directly from the supplied RubricTrajectory.estimated_grade -- "
        "never invented or recomputed here. None if no rubric_trajectory was supplied.",
    )
    priority_coach_issue_id: Optional[str] = Field(
        default=None,
        description="Echoed directly from the supplied PriorityCoach.priority_issue_id, for "
        "traceability against priority_status. None if no priority_coach was supplied.",
    )


def _format_optional(value: Optional[str], not_provided: str) -> str:
    return value if value is not None else not_provided


def _build_messages(
    assignment: str,
    student_work: str,
    rubric: Optional[str],
    teacher_instructions: Optional[str],
    assignment_understanding: Optional[AssignmentUnderstanding],
    success_criteria: Optional[RubricSuccessCriteria],
    student_work_review: Optional[StudentWorkReview],
    rubric_trajectory: Optional[RubricTrajectory],
    priority_coach: Optional[PriorityCoach],
    current_grade: Optional[str],
    priority_coach_issue_id: Optional[str],
) -> list[SystemMessage | HumanMessage]:
    understanding_text = (
        assignment_understanding.model_dump_json(indent=2)
        if assignment_understanding is not None
        else _NOT_PROVIDED
    )
    success_criteria_text = (
        success_criteria.model_dump_json(indent=2) if success_criteria is not None else _NOT_PROVIDED
    )
    student_work_review_text = (
        student_work_review.model_dump_json(indent=2) if student_work_review is not None else _NOT_PROVIDED
    )
    rubric_trajectory_text = (
        rubric_trajectory.model_dump_json(indent=2) if rubric_trajectory is not None else _NOT_PROVIDED
    )
    priority_coach_text = (
        priority_coach.model_dump_json(indent=2) if priority_coach is not None else _NOT_PROVIDED
    )
    human_content = _HUMAN_TEMPLATE.format(
        assignment=assignment,
        rubric=rubric or _NOT_PROVIDED,
        teacher_instructions=teacher_instructions or _NOT_PROVIDED,
        student_work=student_work,
        assignment_understanding=understanding_text,
        success_criteria=success_criteria_text,
        student_work_review=student_work_review_text,
        rubric_trajectory=rubric_trajectory_text,
        priority_coach=priority_coach_text,
        current_grade=_format_optional(current_grade, _NO_TRAJECTORY),
        priority_coach_issue_id=_format_optional(priority_coach_issue_id, _NO_PRIORITY),
    )
    return [SystemMessage(content=SYSTEM_PROMPT_TEXT), HumanMessage(content=human_content)]


def _require_question(text: str, field_label: str, limitations: list[str]) -> None:
    """Deterministic guardrail check -- never silently rewrites the model's
    text (that would itself be the system inventing content), just surfaces
    a violation transparently, the same way an invalid issue id is surfaced
    rather than silently trusted."""
    if not text.strip().endswith("?"):
        limitations.append(
            f"{field_label} did not end with '?' as required and may not be a genuine "
            f"question: {text!r}"
        )


def _flag_invented_percentage(text: str, field_label: str, limitations: list[str]) -> None:
    """Stage 5 must never introduce its own percentage/score -- Rubric
    Trajectory owns that. Flags (does not strip) any percentage-shaped
    figure appearing in judgement prose."""
    if _PERCENT_PATTERN.search(text):
        limitations.append(
            f"{field_label} contains a specific percentage figure, which Stage 5 must not "
            f"introduce (Rubric Trajectory owns percentage estimation): {text!r}"
        )


async def review_toughest_teacher(
    assignment: str,
    student_work: str,
    rubric: Optional[str] = None,
    teacher_instructions: Optional[str] = None,
    assignment_understanding: Optional[AssignmentUnderstanding] = None,
    success_criteria: Optional[RubricSuccessCriteria] = None,
    student_work_review: Optional[StudentWorkReview] = None,
    rubric_trajectory: Optional[RubricTrajectory] = None,
    priority_coach: Optional[PriorityCoach] = None,
    model: Optional[BaseChatModel] = None,
) -> ToughestTeacherReview:
    """Final adversarial review: what would the toughest reasonable teacher
    still challenge before letting this work move into the next grade band?

    ``assignment`` and ``student_work`` are required. Everything else is
    optional: ``rubric``/``teacher_instructions`` are raw source material;
    ``assignment_understanding``/``success_criteria``/``student_work_review``/
    ``rubric_trajectory``/``priority_coach`` are AI-generated upstream
    context, not authoritative over the raw rubric. ``current_grade`` is
    echoed here in Python from ``rubric_trajectory`` -- the model never
    computes or invents a grade/percentage itself. Pass ``model`` to use a
    specific chat model (e.g. a fake one in tests) instead of the default
    from :func:`ammu_review.config.get_model`.
    """
    current_grade = rubric_trajectory.estimated_grade if rubric_trajectory is not None else None
    priority_coach_issue_id = priority_coach.priority_issue_id if priority_coach is not None else None

    llm = model or get_model()
    structured_llm = llm.with_structured_output(_ToughestTeacherDraft)
    messages = _build_messages(
        assignment,
        student_work,
        rubric,
        teacher_instructions,
        assignment_understanding,
        success_criteria,
        student_work_review,
        rubric_trajectory,
        priority_coach,
        current_grade,
        priority_coach_issue_id,
    )
    draft = await structured_llm.ainvoke(messages)

    data = draft.model_dump()
    limitations: list[str] = list(data["limitations"])

    # --- No Stage 4 priority supplied -> priority_status MUST be unset, no ---
    # --- matter what the model says. Ground truth is whether priority_coach ---
    # --- was actually passed in, not the model's own claim.               ---
    if priority_coach is None and data["priority_status"] is not None:
        limitations.append(
            f"The model set priority_status to '{data['priority_status']}' despite no Stage 4 "
            "priority being supplied; this is not something it could actually know, so it has "
            "been cleared."
        )
        data["priority_status"] = None

    # --- Validate every referenced Stage 3 issue id, exactly like Stage 4 ---
    known_ids = {issue.id for issue in student_work_review.issues} if student_work_review is not None else set()
    known_issue_by_id = (
        {issue.id: issue for issue in student_work_review.issues} if student_work_review is not None else {}
    )
    for challenge in data["unresolved_issues"]:
        challenge_issue_id = challenge["issue_id"]
        if challenge_issue_id is not None and challenge_issue_id not in known_ids:
            limitations.append(
                f"The model referenced issue id '{challenge_issue_id}', which does not match "
                "any issue in the supplied Stage 3 review; treating this challenge as not tied "
                "to a specific listed issue."
            )
            challenge["issue_id"] = None
        elif challenge_issue_id is not None:
            # Trust Stage 3's own recorded category over the model's restatement.
            challenge["category"] = known_issue_by_id[challenge_issue_id].category

    # --- Light criterion-code cross-check against Stage 2's success map ---
    known_criterion_codes = (
        {c.code for c in success_criteria.criteria if c.code} if success_criteria is not None else set()
    )
    if known_criterion_codes:
        for challenge in data["unresolved_issues"]:
            for ref in challenge["related_criteria"]:
                code = ref["criterion_code"]
                if code is not None and code not in known_criterion_codes:
                    limitations.append(
                        f"The model referenced rubric criterion code '{code}', which does not "
                        "match any criterion in the supplied Stage 2 success map."
                    )

    # --- Question-format guardrails (never silently rewritten) ---
    _require_question(data["final_student_question"], "final_student_question", limitations)
    for challenge in data["unresolved_issues"]:
        _require_question(
            challenge["student_question"], f"unresolved_issues[rank={challenge['rank']}].student_question", limitations
        )

    # --- No-invented-percentage guardrail across judgement prose ---
    _flag_invented_percentage(data["overall_judgment"], "overall_judgment", limitations)
    _flag_invented_percentage(data["trajectory_challenge"], "trajectory_challenge", limitations)
    _flag_invented_percentage(data["final_improvement_target"], "final_improvement_target", limitations)
    for challenge in data["unresolved_issues"]:
        _flag_invented_percentage(
            challenge["teacher_challenge"], f"unresolved_issues[rank={challenge['rank']}].teacher_challenge", limitations
        )

    data["limitations"] = limitations

    return ToughestTeacherReview(
        **data,
        current_grade=current_grade,
        priority_coach_issue_id=priority_coach_issue_id,
    )
