"""Stage 3: Student Work Review.

Stage 1 answers "what is the task?"; Stage 2 answers "what does success look
like?". This stage answers "how well does Ammu's actual work currently
demonstrate that?" -- it is a REVIEWER, never a writer: it never rewrites her
work or supplies replacement sentences/paragraphs, and it prefers surfacing a
question over stating a conclusion (see north_star in
prompts/03_student_work_review.md, and .ai/PRODUCT.md "Guiding Principles").

Output is deliberately structured (discrete `issues`, per-criterion
`rubric_assessment`) so Stage 4 ("Gap & Priority Review") has something
concrete to triage and prioritise, rather than free-text prose to re-parse.

The prompt that defines this role lives in
``prompts/03_student_work_review.md``, kept separate from this module so the
instructions can be edited without touching code.
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

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "03_student_work_review.md"
SYSTEM_PROMPT_TEXT = PROMPT_PATH.read_text()

_NOT_PROVIDED = "Not provided."

_HUMAN_TEMPLATE = """# Assignment / Task Sheet

{assignment}

# Marking Criteria / Rubric

{rubric}

# Additional Teacher Instructions

{teacher_instructions}

# Stage 1 Assignment Understanding (AI-generated context -- not authoritative)

{assignment_understanding}

# Stage 2 Rubric Success Criteria (AI-generated context -- not authoritative)

{success_criteria}

# Ammu's Submitted Work (the thing you are reviewing)

{student_work}

Analyse Ammu's submitted work following your role and produce the structured review."""


class EvidenceReview(BaseModel):
    """One claim in Ammu's work, checked against the evidence she supplied for it."""

    claim: str = Field(description="The claim Ammu makes, in her own words or closely paraphrased.")
    evidence: str = Field(
        description="The evidence she cites for it, or 'None found in her work.' if she "
        "doesn't support it with anything."
    )
    relationship: Literal["strong", "partial", "weak", "unsupported"] = Field(
        description="How strongly the cited evidence actually supports the claim."
    )
    explanation: str = Field(description="Why this claim/evidence pair got that rating.")
    suggested_thinking: str = Field(
        description="A question for Ammu to think through to strengthen this herself -- "
        "never a rewritten sentence or the evidence itself."
    )


class DimensionReview(BaseModel):
    """One WHAT/HOW/WHY/SO-WHAT dimension of description-vs-analysis."""

    status: Literal["strong", "partial", "missing"] = Field(
        description="Whether this dimension is strongly present, partially present, or missing."
    )
    observation: str = Field(description="What in her work supports this status.")


class AnalysisReview(BaseModel):
    """Description-vs-analysis check across the four classic dimensions."""

    what: DimensionReview = Field(description="Does she explain WHAT happened?")
    how: DimensionReview = Field(description="Does she explain HOW it happened?")
    why: DimensionReview = Field(description="Does she explain WHY it happened?")
    so_what: DimensionReview = Field(
        description="Does she explain SO WHAT -- why it matters/its significance?"
    )


class ReviewIssue(BaseModel):
    """One discrete, structured issue -- designed to be Stage 4's raw material."""

    id: str = Field(
        default="",
        description="Assigned automatically after generation -- do not fill this in.",
    )
    category: Literal["content", "evidence", "analysis", "accuracy", "structure", "grammar", "rubric"] = Field(
        description="What kind of issue this is. Use 'accuracy' for anything about factual "
        "correctness -- including a fact in her work contradicting the supplied assignment/task "
        "material, or an internal contradiction -- even if it's a small detail like a date or "
        "number. Use 'content' for missing, off-topic, or insufficiently developed content, not "
        "for factual correctness. Use 'rubric' only for a gap tied to a specific rubric criterion "
        "that doesn't fit the other categories."
    )
    severity: Literal["critical", "high", "medium", "low"] = Field(
        description="How much this affects meeting the task/rubric -- not how harsh it sounds."
    )
    location: str = Field(
        description="Where in her actual work this applies -- quote or closely paraphrase the "
        "relevant part. Never just 'throughout'."
    )
    observation: str = Field(description="What's actually there.")
    why_it_matters: str = Field(
        description="Why this matters, tied back to the task or rubric -- not generic writing advice."
    )
    student_question: str = Field(
        description="A genuine question for Ammu to think through herself. Must be phrased as an "
        "actual question, never a rewritten sentence or an instruction in disguise."
    )


class RubricAssessment(BaseModel):
    """Where Ammu's current work sits against one rubric criterion."""

    criterion_code: Optional[str] = Field(
        default=None, description="The rubric's own outcome code, if it has one (e.g. '5.3')."
    )
    criterion_name: str = Field(description="The criterion's own name, verbatim from the rubric.")
    current_level: str = Field(
        description="The rubric's OWN band label that Ammu's current work appears to sit at "
        "(e.g. 'Sound', not a generic scale) -- or a plain statement that this can't be "
        "determined, if the rubric or her work don't give enough to judge."
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="How confident this assessment is -- low if the supplied work is too short "
        "or ambiguous to judge well."
    )
    evidence: list[str] = Field(
        description="What in her actual work supports this level assessment."
    )
    gap_to_next_level: list[str] = Field(
        description="What's missing to reach the next band up, described as a gap to close -- "
        "never as a rewritten sentence that would close it."
    )


class StudentWorkReview(BaseModel):
    """How well Ammu's actual submitted work currently demonstrates what's being asked."""

    strengths: list[str] = Field(
        description="What her work already does well, grounded in specific parts of it -- not "
        "generic praise."
    )
    task_alignment: str = Field(
        description="How well the work addresses the task's actual requirements. Note any "
        "requirement that appears unaddressed or only partially addressed."
    )
    rubric_assessment: list[RubricAssessment] = Field(
        description="One entry per rubric criterion. Empty, with the limitation stated in "
        "`limitations`, if no rubric or Stage 2 success map was supplied."
    )
    evidence_reviews: list[EvidenceReview] = Field(
        description="Claim-by-claim evidence checks for the claims Ammu actually makes."
    )
    analysis_review: AnalysisReview = Field(
        description="The WHAT/HOW/WHY/SO-WHAT description-vs-analysis check."
    )
    issues: list[ReviewIssue] = Field(
        description="Discrete, structured issues compiled from the above -- this is the input "
        "Stage 4 will triage and prioritise."
    )
    limitations: list[str] = Field(
        description="Explicit statements of what could not be assessed -- e.g. no rubric was "
        "supplied, the work is too short to judge a dimension, or a claim's accuracy can't be "
        "verified from the supplied material. Never fill these gaps with generic assumptions."
    )


def _build_messages(
    assignment: str,
    student_work: str,
    rubric: Optional[str],
    teacher_instructions: Optional[str],
    assignment_understanding: Optional[AssignmentUnderstanding],
    success_criteria: Optional[RubricSuccessCriteria],
) -> list[SystemMessage | HumanMessage]:
    understanding_text = (
        assignment_understanding.model_dump_json(indent=2)
        if assignment_understanding is not None
        else _NOT_PROVIDED
    )
    success_criteria_text = (
        success_criteria.model_dump_json(indent=2) if success_criteria is not None else _NOT_PROVIDED
    )
    human_content = _HUMAN_TEMPLATE.format(
        assignment=assignment,
        rubric=rubric or _NOT_PROVIDED,
        teacher_instructions=teacher_instructions or _NOT_PROVIDED,
        assignment_understanding=understanding_text,
        success_criteria=success_criteria_text,
        student_work=student_work,
    )
    return [SystemMessage(content=SYSTEM_PROMPT_TEXT), HumanMessage(content=human_content)]


async def review_student_work(
    assignment: str,
    student_work: str,
    rubric: Optional[str] = None,
    teacher_instructions: Optional[str] = None,
    assignment_understanding: Optional[AssignmentUnderstanding] = None,
    success_criteria: Optional[RubricSuccessCriteria] = None,
    model: Optional[BaseChatModel] = None,
) -> StudentWorkReview:
    """Assess how well Ammu's actual submitted work demonstrates what's being asked.

    ``student_work`` is required -- there is nothing to review without it.
    ``rubric``, ``teacher_instructions``, ``assignment_understanding`` and
    ``success_criteria`` are all optional context; Stage 1/2 results are passed
    through as AI-generated context, not treated as authoritative over the raw
    assignment/rubric text. Pass ``model`` to use a specific chat model (e.g. a
    fake one in tests) instead of the default from
    :func:`ammu_review.config.get_model`.
    """
    llm = model or get_model()
    structured_llm = llm.with_structured_output(StudentWorkReview)
    messages = _build_messages(
        assignment, student_work, rubric, teacher_instructions, assignment_understanding, success_criteria
    )
    result = await structured_llm.ainvoke(messages)

    # Ids are assigned here, not by the model -- deterministic and guaranteed
    # unique, so Stage 4 can reference them reliably.
    for i, issue in enumerate(result.issues, start=1):
        issue.id = f"S3-ISSUE-{i}"

    return result


# ---------------------------------------------------------------------------
# Rubric Trajectory -- an ADDITIVE capability alongside Stage 3, added after
# Stage 3 itself was frozen. Nothing above this line was changed to add it:
# it is a fully separate function/model, not a new field bolted onto
# StudentWorkReview, so the frozen Stage 3 schema/behaviour/guardrails are
# untouched. It reuses Stage 1/2 outputs as context exactly like Stage 3
# does, but does NOT consume Stage 3's own StudentWorkReview -- it is an
# independent re-assessment against the rubric, not a step chained after the
# main review.
#
# Prompt: prompts/03b_rubric_trajectory.md
# ---------------------------------------------------------------------------

TRAJECTORY_PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "03b_rubric_trajectory.md"
TRAJECTORY_SYSTEM_PROMPT_TEXT = TRAJECTORY_PROMPT_PATH.read_text()

_TRAJECTORY_HUMAN_TEMPLATE = """# Assignment / Task Sheet

{assignment}

# Marking Criteria / Rubric

{rubric}

# Additional Teacher Instructions

{teacher_instructions}

# Stage 1 Assignment Understanding (AI-generated context -- not authoritative)

{assignment_understanding}

# Stage 2 Rubric Success Criteria (AI-generated context -- not authoritative)

{success_criteria}

# Ammu's Submitted Work (the thing you are assessing)

{student_work}

Analyse Ammu's submitted work against the rubric following your role and produce the structured trajectory."""

# Grade label -> minimum percent (inclusive) required for that grade. Checked
# in descending order of minimum percent; the grade logic never hardcodes
# these values, so a caller can pass a different scheme entirely.
GradeBoundary = tuple[str, float]
DEFAULT_GRADE_BOUNDARIES: tuple[GradeBoundary, ...] = (
    ("A", 90.0),
    ("B", 70.0),
    ("C", 50.0),
    ("D", 0.0),
)


def grade_for_percent(
    percent: Optional[float],
    boundaries: tuple[GradeBoundary, ...] = DEFAULT_GRADE_BOUNDARIES,
) -> Optional[str]:
    """Map an estimated percent to a grade label using configurable boundaries.

    Returns None if ``percent`` is None (no meaningful estimate was possible)
    or if it falls below every boundary's minimum. Boundaries are re-sorted by
    descending minimum here, so callers don't need to pre-sort them.
    """
    if percent is None:
        return None
    for label, minimum in sorted(boundaries, key=lambda b: b[1], reverse=True):
        if percent >= minimum:
            return label
    return None


class CriterionTrajectory(BaseModel):
    """One rubric criterion's estimated trajectory, assessed independently."""

    criterion_code: Optional[str] = Field(
        default=None, description="The rubric's own outcome code, if it has one (e.g. '5.3')."
    )
    criterion_name: str = Field(description="The criterion's own name, verbatim from the rubric.")
    estimated_score_percent: Optional[float] = Field(
        default=None,
        description="An estimated percentage (0-100) of this criterion's available marks that "
        "Ammu's current work appears to demonstrate, grounded directly in the rubric's own band "
        "descriptors and specific evidence from her actual work. This is an ESTIMATE, never a "
        "prediction of the teacher's actual mark -- never present it with false precision. None "
        "if the rubric doesn't support a meaningful percentage for this criterion (explain why "
        "in `limitation`).",
    )
    confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence in this estimate -- low if the evidence is thin or the rubric's "
        "wording for this criterion is vague."
    )
    rationale: str = Field(
        description="Why this estimate (or lack of one), grounded in the rubric's own band "
        "descriptors and specific evidence from her actual work -- not generic."
    )
    limitation: Optional[str] = Field(
        default=None,
        description="Set only when estimated_score_percent is None -- explain specifically why "
        "this criterion cannot be given a meaningful percentage.",
    )


class _RubricTrajectoryDraft(BaseModel):
    """What the model produces. `estimated_grade`/`grade_boundaries_used` are
    computed afterward in Python from configured boundaries -- never by the
    model -- so they're deliberately not part of this schema."""

    rubric_provided: bool = Field(
        description="Whether an actual marking rubric was supplied. False whenever the "
        "'Marking Criteria / Rubric' input was 'Not provided.'."
    )
    criteria: list[CriterionTrajectory] = Field(
        description="One entry per rubric criterion. Must be empty if rubric_provided is False."
    )
    overall_estimated_score_percent: Optional[float] = Field(
        default=None,
        description="An estimated overall percentage (0-100) of the rubric Ammu's current work "
        "appears to satisfy, weighing the criteria holistically -- not necessarily a mechanical "
        "average, reflecting any relative emphasis the rubric itself implies (e.g. marks "
        "allocated per criterion). This is an ESTIMATED TRAJECTORY, never a prediction of the "
        "teacher's actual mark -- never present it with false precision or certainty. None if "
        "the rubric doesn't give enough information to support a meaningful overall percentage "
        "(state why in `limitations`). Do not compute or state a letter grade yourself.",
    )
    overall_confidence: Literal["low", "medium", "high"] = Field(
        description="Confidence in the overall estimate."
    )
    biggest_opportunity: str = Field(
        description="The single biggest opportunity to move Ammu's work toward the next grade "
        "boundary -- described as something for her to think about and act on herself, never a "
        "rewritten sentence or ready-to-submit content."
    )
    next_boundary_requirements: list[str] = Field(
        description="What would need to change, in terms of demonstrating the rubric's "
        "criteria, to reach the next grade boundary up -- concrete gaps to close, never "
        "rewritten sentences or content she could copy in."
    )
    limitations: list[str] = Field(
        description="Explicit statements of what could not be estimated and why -- e.g. no "
        "rubric was supplied, or the rubric doesn't specify enough (like marks/weights) to "
        "support a meaningful percentage. If no rubric was supplied, this must contain exactly "
        "this single entry, verbatim: 'Rubric trajectory cannot be estimated because no marking "
        "rubric was supplied.' Never fill these gaps with generic assumptions."
    )


class RubricTrajectory(_RubricTrajectoryDraft):
    """Public result: the model's draft plus the grade computed in Python."""

    estimated_grade: Optional[str] = Field(
        default=None,
        description="Computed in Python from overall_estimated_score_percent and the configured "
        "grade boundaries -- never filled in by the model.",
    )
    grade_boundaries_used: list[GradeBoundary] = Field(
        default_factory=list,
        description="The grade boundaries actually used to compute estimated_grade, for "
        "transparency about how the estimate maps to a letter.",
    )


def _build_trajectory_messages(
    assignment: str,
    student_work: str,
    rubric: Optional[str],
    teacher_instructions: Optional[str],
    assignment_understanding: Optional[AssignmentUnderstanding],
    success_criteria: Optional[RubricSuccessCriteria],
) -> list[SystemMessage | HumanMessage]:
    understanding_text = (
        assignment_understanding.model_dump_json(indent=2)
        if assignment_understanding is not None
        else _NOT_PROVIDED
    )
    success_criteria_text = (
        success_criteria.model_dump_json(indent=2) if success_criteria is not None else _NOT_PROVIDED
    )
    human_content = _TRAJECTORY_HUMAN_TEMPLATE.format(
        assignment=assignment,
        rubric=rubric or _NOT_PROVIDED,
        teacher_instructions=teacher_instructions or _NOT_PROVIDED,
        assignment_understanding=understanding_text,
        success_criteria=success_criteria_text,
        student_work=student_work,
    )
    return [SystemMessage(content=TRAJECTORY_SYSTEM_PROMPT_TEXT), HumanMessage(content=human_content)]


async def review_rubric_trajectory(
    assignment: str,
    student_work: str,
    rubric: Optional[str] = None,
    teacher_instructions: Optional[str] = None,
    assignment_understanding: Optional[AssignmentUnderstanding] = None,
    success_criteria: Optional[RubricSuccessCriteria] = None,
    grade_boundaries: tuple[GradeBoundary, ...] = DEFAULT_GRADE_BOUNDARIES,
    model: Optional[BaseChatModel] = None,
) -> RubricTrajectory:
    """Estimate where Ammu's current work sits against the rubric, as a grade trajectory.

    This is an estimate, not a prediction of the teacher's actual mark. Grade
    boundaries are configurable via ``grade_boundaries`` (default: A>=90,
    B>=70, C>=50, D<50) and are applied here in Python, deterministically --
    the model never computes or states a letter grade itself.

    ``student_work`` is required. ``rubric``, ``teacher_instructions``,
    ``assignment_understanding`` and ``success_criteria`` are all optional
    context, exactly as in :func:`review_student_work` -- but this function
    does not consume Stage 3's own result; it assesses independently from the
    same raw inputs. Pass ``model`` to use a specific chat model (e.g. a fake
    one in tests) instead of the default from
    :func:`ammu_review.config.get_model`.
    """
    llm = model or get_model()
    structured_llm = llm.with_structured_output(_RubricTrajectoryDraft)
    messages = _build_trajectory_messages(
        assignment, student_work, rubric, teacher_instructions, assignment_understanding, success_criteria
    )
    draft = await structured_llm.ainvoke(messages)

    sorted_boundaries = sorted(grade_boundaries, key=lambda b: b[1], reverse=True)
    return RubricTrajectory(
        **draft.model_dump(),
        estimated_grade=grade_for_percent(draft.overall_estimated_score_percent, grade_boundaries),
        grade_boundaries_used=sorted_boundaries,
    )
