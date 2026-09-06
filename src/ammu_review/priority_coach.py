"""Stage 4: Priority Coach.

Stage 3 is the diagnostic reviewer: "what is wrong or missing?" It can
surface many issues. Stage 4 does not re-review the work -- it is the
prioritizer/coach: "what should Ammu work on FIRST?" It selects exactly one
priority from Stage 3's (and Rubric Trajectory's) output and coaches Ammu
toward it with a single question, never an answer.

This is a fully additive, new stage -- it does not modify Stage 1, Stage 2,
Stage 3, or Rubric Trajectory. It only *consumes* their results as either
source material (assignment/rubric/student work) or AI-generated context
(Stage 1/2/3/Trajectory results, explicitly not authoritative -- the rubric
remains the sole authority).

Design reference: .ai/STAGE_4_PRIORITY_COACH_DESIGN.md

The prompt that defines this role lives in ``prompts/04_priority_coach.md``,
kept separate from this module so the instructions can be edited without
touching code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from .assignment_understanding import AssignmentUnderstanding
from .config import get_model
from .rubric_success_criteria import RubricSuccessCriteria
from .student_work_review import GradeBoundary, RubricTrajectory, StudentWorkReview

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "04_priority_coach.md"
SYSTEM_PROMPT_TEXT = PROMPT_PATH.read_text()

_NOT_PROVIDED = "Not provided."

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

## Already-computed grade-boundary context (do not recompute or second-guess this)

Current estimated position: {current_grade}
Next grade boundary to aim for: {target_grade}

Select the single highest-priority issue following your role and produce the structured coaching output."""


class CriterionRef(BaseModel):
    """A rubric criterion identity -- reused wherever a criterion needs to be
    referenced, matching the code+name pair pattern already used by
    RubricAssessment (Stage 3) and CriterionTrajectory (Rubric Trajectory)."""

    criterion_code: Optional[str] = Field(
        default=None, description="The rubric's own outcome code, if it has one (e.g. '5.3')."
    )
    criterion_name: str = Field(description="The criterion's own name, verbatim from the rubric.")


class _PriorityCoachDraft(BaseModel):
    """What the model produces. ``current_grade``/``target_grade`` are NOT
    here -- they're computed in Python from the supplied RubricTrajectory
    before the model is even called, exactly like RubricTrajectory's own
    ``estimated_grade`` is computed from a percent, never asked of a model."""

    priority_issue_id: Optional[str] = Field(
        default=None,
        description="References one of the supplied Stage 3 review's issue ids (e.g. "
        "'S3-ISSUE-4'), ONLY if the chosen priority corresponds to a specific listed Stage 3 "
        "issue. None if no Stage 3 review was supplied, or the priority is a broader pattern "
        "not tied to one specific issue. Validated in Python after generation -- an id that "
        "doesn't match a real supplied issue will be discarded, not trusted.",
    )
    priority_statement: str = Field(
        description="A self-contained one/two-sentence statement of the ONE priority -- must "
        "make sense even if priority_issue_id is unset."
    )
    priority_category: Literal["content", "evidence", "analysis", "accuracy", "structure", "grammar", "rubric"] = (
        Field(
            description="Same categories as Stage 3's issue categories. If priority_issue_id "
            "resolves to a real Stage 3 issue, this is overwritten in Python from that issue's "
            "actual category -- your value here is only used when there's no matching issue to "
            "defer to."
        )
    )
    why_this_matters: str = Field(
        description="Grounded in the task/rubric -- why THIS, specifically, not a generic "
        "'this is important' statement. Explain why it beat the other issues, per the priority "
        "selection logic."
    )
    primary_criterion: CriterionRef = Field(
        description="The main rubric criterion this priority affects."
    )
    also_affects_criteria: list[CriterionRef] = Field(
        default_factory=list,
        description="Other criteria fixing this would plausibly and directly help -- be "
        "conservative, do not list a criterion just because it's tangentially related.",
    )
    trajectory_connection: str = Field(
        description="How addressing this priority relates to moving from the current grade "
        "toward the next boundary. Must use hedged language ('is likely to strengthen your "
        "position toward the X range') -- NEVER a specific point/percentage increase. If no "
        "trajectory context was supplied (the 'Current estimated position' given to you says "
        "'Not available'), this field must be EXACTLY, verbatim, this sentence and nothing "
        "else: 'Trajectory framing is not available because no Rubric Trajectory context was "
        "supplied.' Do not write a generic 'this will help' statement instead."
    )
    student_question: str = Field(
        description="THE one primary question for Ammu. Must genuinely require thinking, "
        "relate directly to the selected priority, be answerable from the assignment/her own "
        "research, end with '?', and must NOT contain or imply the answer, and must NOT be a "
        "disguised instruction to write or copy a particular sentence."
    )
    improvement_target: str = Field(
        description="Describes the QUALITY of thinking/evidence a successful revision would "
        "demonstrate -- never the actual content of the answer. E.g. 'Your revised section "
        "should move beyond describing X and demonstrate a justified evaluation of Y, using "
        "relevant evidence' -- never 'Add that X happened, so Y.'"
    )
    evidence_to_consider: list[str] = Field(
        default_factory=list,
        description="The KIND/DIRECTION of evidence Ammu could look at -- never a stated "
        "conclusion about what that evidence shows.",
    )
    other_issues_deferred: list[str] = Field(
        default_factory=list,
        description="Brief acknowledgement that other issues exist -- reference their Stage 3 "
        "ids where available, otherwise a short label. One short line each, at most. This must "
        "NOT reproduce Stage 3's full review.",
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence in this being the right priority to focus on. Lower this if "
        "the rubric wording for the affected criterion was already reported as ambiguous or "
        "incomplete by Stage 2/3."
    )
    limitations: list[str] = Field(
        default_factory=list,
        description="Explicit statements of what could not be determined -- e.g. no Stage 3 "
        "review was supplied so no issue id could be referenced, no rubric was supplied, or no "
        "trajectory context was supplied. Never fill these gaps with generic assumptions.",
    )


class PriorityCoach(_PriorityCoachDraft):
    """Public result: the model's draft plus grade-boundary context computed
    in Python -- never asked of the model."""

    current_grade: Optional[str] = Field(
        default=None,
        description="Ammu's current estimated grade, taken directly from the supplied "
        "RubricTrajectory.estimated_grade. None if no rubric_trajectory was supplied.",
    )
    target_grade: Optional[str] = Field(
        default=None,
        description="The next grade boundary up from current_grade, computed by "
        "next_grade_up() using RubricTrajectory.grade_boundaries_used. Equal to current_grade "
        "if already at the top boundary (maintain/strengthen). None if current_grade is None.",
    )


def next_grade_up(
    current_grade: Optional[str],
    boundaries_sorted_desc: list[GradeBoundary],
) -> Optional[str]:
    """Return the grade label one position above ``current_grade``.

    ``boundaries_sorted_desc`` is expected sorted descending by minimum
    percent (exactly the shape of ``RubricTrajectory.grade_boundaries_used``).
    Returns ``current_grade`` itself if it's already the top boundary (the
    "maintain/strengthen" case), or None if ``current_grade`` is None or
    doesn't appear in the boundaries. This is pure Python -- the model never
    computes or invents grade-boundary transitions.
    """
    if current_grade is None or not boundaries_sorted_desc:
        return None
    labels = [label for label, _ in boundaries_sorted_desc]
    if current_grade not in labels:
        return None
    index = labels.index(current_grade)
    if index == 0:
        return current_grade
    return labels[index - 1]


def _format_grade(grade: Optional[str]) -> str:
    if grade is None:
        return "Not available -- no Rubric Trajectory context was supplied."
    return grade


def _build_messages(
    assignment: str,
    student_work: str,
    rubric: Optional[str],
    teacher_instructions: Optional[str],
    assignment_understanding: Optional[AssignmentUnderstanding],
    success_criteria: Optional[RubricSuccessCriteria],
    student_work_review: Optional[StudentWorkReview],
    rubric_trajectory: Optional[RubricTrajectory],
    current_grade: Optional[str],
    target_grade: Optional[str],
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
    human_content = _HUMAN_TEMPLATE.format(
        assignment=assignment,
        rubric=rubric or _NOT_PROVIDED,
        teacher_instructions=teacher_instructions or _NOT_PROVIDED,
        student_work=student_work,
        assignment_understanding=understanding_text,
        success_criteria=success_criteria_text,
        student_work_review=student_work_review_text,
        rubric_trajectory=rubric_trajectory_text,
        current_grade=_format_grade(current_grade),
        target_grade=_format_grade(target_grade),
    )
    return [SystemMessage(content=SYSTEM_PROMPT_TEXT), HumanMessage(content=human_content)]


async def review_priority_coach(
    assignment: str,
    student_work: str,
    rubric: Optional[str] = None,
    teacher_instructions: Optional[str] = None,
    assignment_understanding: Optional[AssignmentUnderstanding] = None,
    success_criteria: Optional[RubricSuccessCriteria] = None,
    student_work_review: Optional[StudentWorkReview] = None,
    rubric_trajectory: Optional[RubricTrajectory] = None,
    model: Optional[BaseChatModel] = None,
) -> PriorityCoach:
    """Select the single highest-priority next step for Ammu, and coach her
    toward it with one question -- never an answer.

    ``assignment`` and ``student_work`` are required. Everything else is
    optional: ``rubric``/``teacher_instructions`` are raw source material;
    ``assignment_understanding``/``success_criteria``/``student_work_review``/
    ``rubric_trajectory`` are AI-generated upstream context, not authoritative
    over the raw rubric. ``current_grade``/``target_grade`` are computed here
    in Python from ``rubric_trajectory`` -- the model never computes or
    states a grade boundary itself. Pass ``model`` to use a specific chat
    model (e.g. a fake one in tests) instead of the default from
    :func:`ammu_review.config.get_model`.
    """
    current_grade = rubric_trajectory.estimated_grade if rubric_trajectory is not None else None
    target_grade = (
        next_grade_up(current_grade, rubric_trajectory.grade_boundaries_used)
        if rubric_trajectory is not None
        else None
    )

    llm = model or get_model()
    structured_llm = llm.with_structured_output(_PriorityCoachDraft)
    messages = _build_messages(
        assignment,
        student_work,
        rubric,
        teacher_instructions,
        assignment_understanding,
        success_criteria,
        student_work_review,
        rubric_trajectory,
        current_grade,
        target_grade,
    )
    draft = await structured_llm.ainvoke(messages)

    # Validate the referenced Stage 3 issue id against the real supplied
    # issues -- never let a hallucinated/mismatched id leak into the public
    # result the future revision loop would trust.
    known_ids = {issue.id for issue in student_work_review.issues} if student_work_review is not None else set()
    data = draft.model_dump()

    if draft.priority_issue_id is not None and draft.priority_issue_id not in known_ids:
        data["limitations"] = [
            *data["limitations"],
            f"The model referenced issue id '{draft.priority_issue_id}', which does not match "
            "any issue in the supplied Stage 3 review; treating the priority as not tied to a "
            "specific listed issue.",
        ]
        data["priority_issue_id"] = None
        # No real issue to defer to -- keep the model's own category judgement.
    elif draft.priority_issue_id is not None:
        # Trust Stage 3's own recorded category over the model's restatement.
        matched_issue = next(issue for issue in student_work_review.issues if issue.id == draft.priority_issue_id)
        data["priority_category"] = matched_issue.category

    return PriorityCoach(**data, current_grade=current_grade, target_grade=target_grade)
