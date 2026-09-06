"""Stage 1: Assignment Understanding Reviewer.

Explains what a teacher is actually asking a student to do, before she starts
writing -- it never solves the assignment or drafts answerable text. The
prompt that defines this role lives in ``prompts/01_assignment_understanding.md``,
kept separate from this module so the instructions can be edited without
touching code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from .config import get_model

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "01_assignment_understanding.md"
SYSTEM_PROMPT_TEXT = PROMPT_PATH.read_text()

_NOT_PROVIDED = "Not provided."

_HUMAN_TEMPLATE = """# Assignment / Task Sheet

{assignment}

# Marking Criteria / Rubric

{rubric}

# Additional Teacher Instructions

{teacher_instructions}

Analyse this assignment following your role and produce the structured output."""


class AssignmentUnderstanding(BaseModel):
    """What the teacher is actually asking for, before the student writes anything."""

    main_task: str = Field(
        description="Plain-language explanation of what the teacher is actually asking "
        "the student to do, in terms a Grade 9 student can understand."
    )
    requirements: list[str] = Field(
        description="Explicit requirements stated or clearly implied by the task "
        "instructions (topics, evidence, structure, word count, format, etc.)."
    )
    assessed_skills: list[str] = Field(
        description="The rubric's OWN explicit assessment criteria -- outcome codes, "
        "labels, or descriptors -- preserving its terminology (e.g. "
        "'5.3 — Examines the role of law in society'). Do not replace the rubric's own "
        "terms with a generic taxonomy such as Knowledge/Understanding/Analysis/"
        "Evidence/Evaluation/Communication; a generic label may only be added if the "
        "rubric genuinely supports it, never as a substitute for what it actually says. "
        "Assessment criteria can ONLY come from an actual marking rubric -- never "
        "inferred or reverse-engineered from the assignment text itself. If no rubric "
        "was supplied, this must never be empty, never fall back to a generic "
        "taxonomy, and never be inferred from the assignment -- output exactly this "
        "single entry, verbatim: 'Assessment criteria cannot be determined because no "
        "marking rubric was supplied.'"
    )
    command_words: list[str] = Field(
        description="Important command words from the task (e.g. 'analyse', 'evaluate'), "
        "each followed by an explanation of what it actually requires the student to do."
    )
    hidden_traps: list[str] = Field(
        description="Ways a good student could still lose marks on this specific "
        "assignment (e.g. answering only part of the question, describing instead of "
        "analysing)."
    )
    top_band_thinking: list[str] = Field(
        description="What Ammu would need to demonstrate to satisfy the highest "
        "relevant level of the supplied rubric, grounded in the rubric's own top-band "
        "descriptors and terminology -- not generic 'write a high quality answer' "
        "advice. The type of thinking required, not the answer itself. Top-band "
        "expectations can ONLY come from an actual marking rubric -- never inferred "
        "from the assignment text. If no rubric was supplied, output exactly this "
        "single entry, verbatim: 'Top-band expectations cannot be determined because "
        "no marking rubric was supplied.'"
    )
    checklist: list[str] = Field(
        description="A short, practical checklist of things to keep in mind before "
        "starting to write."
    )


def _build_messages(
    assignment: str,
    rubric: Optional[str],
    teacher_instructions: Optional[str],
) -> list[SystemMessage | HumanMessage]:
    human_content = _HUMAN_TEMPLATE.format(
        assignment=assignment,
        rubric=rubric or _NOT_PROVIDED,
        teacher_instructions=teacher_instructions or _NOT_PROVIDED,
    )
    return [SystemMessage(content=SYSTEM_PROMPT_TEXT), HumanMessage(content=human_content)]


async def review_assignment(
    assignment: str,
    rubric: Optional[str] = None,
    teacher_instructions: Optional[str] = None,
    model: Optional[BaseChatModel] = None,
) -> AssignmentUnderstanding:
    """Explain what the teacher is asking for, before the student starts writing.

    ``rubric`` and ``teacher_instructions`` are optional -- when omitted, the model
    is told so explicitly rather than left to guess. Pass ``model`` to use a
    specific chat model (e.g. a fake one in tests) instead of the default from
    :func:`ammu_review.config.get_model`.
    """
    llm = model or get_model()
    structured_llm = llm.with_structured_output(AssignmentUnderstanding)
    messages = _build_messages(assignment, rubric, teacher_instructions)
    return await structured_llm.ainvoke(messages)
