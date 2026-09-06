"""Stage 2: Rubric / Success Criteria Reviewer.

Stage 1 (assignment_understanding.py) answers "what is the task?". This
stage answers "how will my teacher decide whether my work is excellent?" --
it turns the teacher's marking rubric into a practical, student-friendly
success map. It never writes the assignment or tells Ammu what content to
produce. The prompt that defines this role lives in
``prompts/02_rubric_success_criteria.md``, kept separate from this module
so the instructions can be edited without touching code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from .assignment_understanding import AssignmentUnderstanding
from .config import get_model

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "02_rubric_success_criteria.md"
SYSTEM_PROMPT_TEXT = PROMPT_PATH.read_text()

_NOT_PROVIDED = "Not provided."

_HUMAN_TEMPLATE = """# Assignment / Task Sheet

{assignment}

# Marking Criteria / Rubric

{rubric}

# Additional Teacher Instructions

{teacher_instructions}

# Stage 1 Assignment Understanding (AI-generated context -- not a marking criterion)

{assignment_understanding}

Analyse the supplied rubric following your role and produce the structured success map."""


class RubricCriterion(BaseModel):
    """One explicit criterion/outcome extracted from the supplied rubric."""

    code: Optional[str] = Field(
        default=None,
        description="The rubric's own outcome code, verbatim, if it has one (e.g. "
        "'5.3'). None if the rubric names this criterion without a code.",
    )
    name: str = Field(
        description="The criterion's own name/title, verbatim or near-verbatim from "
        "the rubric (e.g. 'Examines the role of law in society'). Never a generic "
        "label such as 'Knowledge' or 'Analysis' unless that is literally the rubric's "
        "own wording."
    )
    teacher_wording: str = Field(
        description="The rubric's own descriptor text for this criterion, quoted or "
        "closely paraphrased -- not replaced with generic language."
    )
    student_friendly_meaning: str = Field(
        description="What this criterion actually means, in language a Grade 9 "
        "student can understand, without changing its meaning."
    )
    observable_evidence: list[str] = Field(
        description="Observable characteristics in Ammu's eventual work that would "
        "demonstrate this criterion -- the KIND of thing to look for, never the "
        "actual content, evidence, or argument to put in the assignment."
    )
    top_band_requirements: list[str] = Field(
        description="What the rubric's highest performance level for this criterion "
        "actually requires, grounded directly in its own top-band descriptor."
    )
    good_vs_outstanding: str = Field(
        description="The meaningful difference between a good/average response and "
        "an outstanding one for this criterion, ONLY where the rubric's own wording "
        "supports drawing that distinction. If the rubric doesn't give enough "
        "information, state that plainly instead of inventing a distinction."
    )
    common_failure_modes: list[str] = Field(
        description="Likely ways a student could fail to demonstrate this criterion, "
        "derived from the rubric's lower-band descriptors and/or the assignment "
        "instructions -- not generic filler."
    )


class RubricSuccessCriteria(BaseModel):
    """A practical, student-friendly success map derived from the teacher's rubric."""

    rubric_provided: bool = Field(
        description="Whether an actual marking rubric was supplied. False whenever "
        "the 'Marking Criteria / Rubric' input was 'Not provided.'."
    )
    criteria: list[RubricCriterion] = Field(
        description="One entry per explicit criterion/outcome in the supplied "
        "rubric. Must be empty if rubric_provided is False -- see `limitations` "
        "instead of inventing placeholder criteria."
    )
    overall_top_band_profile: str = Field(
        description="A short synthesis, across all criteria, of what an overall "
        "top-band response looks like -- grounded only in the rubric. If "
        "rubric_provided is False, state that this cannot be determined without a "
        "rubric."
    )
    success_checklist: list[str] = Field(
        description="A concise checklist Ammu can use while writing, phrased as "
        "self-checks against the RUBRIC's criteria (e.g. 'Does my analysis clearly "
        "link summary, outcome, and justification, per 5.3?'). This must NOT restate "
        "the assignment's procedural task steps (choosing a topic, collecting N "
        "sources, hitting a word count) -- that is Stage 1's job; repeating it here "
        "would make this stage redundant with Stage 1. Empty if rubric_provided is "
        "False."
    )
    limitations: list[str] = Field(
        description="Explicit statements of what could not be determined -- e.g. "
        "'no rubric was supplied', or a specific criterion's rubric wording is too "
        "ambiguous or incomplete to determine a good-vs-outstanding distinction or "
        "top-band requirement. Never fill these gaps with generic assumptions; state "
        "the limitation instead."
    )


def _build_messages(
    assignment: str,
    rubric: Optional[str],
    teacher_instructions: Optional[str],
    assignment_understanding: Optional[AssignmentUnderstanding],
) -> list[SystemMessage | HumanMessage]:
    understanding_text = (
        assignment_understanding.model_dump_json(indent=2)
        if assignment_understanding is not None
        else _NOT_PROVIDED
    )
    human_content = _HUMAN_TEMPLATE.format(
        assignment=assignment,
        rubric=rubric or _NOT_PROVIDED,
        teacher_instructions=teacher_instructions or _NOT_PROVIDED,
        assignment_understanding=understanding_text,
    )
    return [SystemMessage(content=SYSTEM_PROMPT_TEXT), HumanMessage(content=human_content)]


async def review_rubric_success_criteria(
    assignment: str,
    rubric: Optional[str] = None,
    teacher_instructions: Optional[str] = None,
    assignment_understanding: Optional[AssignmentUnderstanding] = None,
    model: Optional[BaseChatModel] = None,
) -> RubricSuccessCriteria:
    """Turn the teacher's rubric into a practical, student-friendly success map.

    ``rubric``, ``teacher_instructions`` and ``assignment_understanding`` are all
    optional. ``assignment_understanding`` (Stage 1's result) is passed through as
    context only -- the rubric remains the sole authority for assessment criteria.
    Pass ``model`` to use a specific chat model (e.g. a fake one in tests) instead
    of the default from :func:`ammu_review.config.get_model`.
    """
    llm = model or get_model()
    structured_llm = llm.with_structured_output(RubricSuccessCriteria)
    messages = _build_messages(assignment, rubric, teacher_instructions, assignment_understanding)
    return await structured_llm.ainvoke(messages)
