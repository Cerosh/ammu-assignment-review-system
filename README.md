# Ammu Assignment Review System

An AI-assisted assignment review system, built incrementally with LangChain.

It reviews and challenges a student's work — it does not write it for her.

## Status

**V0.1, Stages 1–5: Assignment Understanding, Rubric / Success Criteria,
Student Work Review, Priority Coach, Toughest Teacher Review** (plus the
Rubric Trajectory capability added onto Stage 3). This is the final
planned review stage — the AI review engine is now considered
feature-complete. The revision-tracking loop, interactive coaching, a UI,
and a controlled pilot are future phases, not implemented yet.

Stages 1–5 and Rubric Trajectory are frozen — their behavior, schema, and
guardrails should not change unless a real defect is found or the user
explicitly unfreezes one.

## Stage 1: Assignment Understanding Reviewer

Given an assignment/task sheet, and optionally a marking rubric and extra
teacher instructions, this stage explains what the teacher is actually
asking the student to do — *before* she starts writing. It never solves the
assignment, drafts answerable sentences, or invents requirements that aren't
actually in the task or rubric.

- Prompt: [`prompts/01_assignment_understanding.md`](prompts/01_assignment_understanding.md)
  (kept separate from code — edit the instructions there, not in Python).
- Implementation: [`src/ammu_review/assignment_understanding.py`](src/ammu_review/assignment_understanding.py)
- Structured output model: `AssignmentUnderstanding` (`main_task`,
  `requirements`, `assessed_skills`, `command_words`, `hidden_traps`,
  `top_band_thinking`, `checklist`).

### Usage

```python
import asyncio
from ammu_review import review_assignment

async def main():
    result = await review_assignment(
        assignment=assignment_text,
        rubric=rubric_text,              # optional
        teacher_instructions=None,       # optional
    )
    print(result.model_dump_json(indent=2))

asyncio.run(main())
```

## Stage 2: Rubric / Success Criteria Reviewer

Stage 1 answers "what is the task?"; Stage 2 answers "how will my teacher
decide whether my work is excellent?" It turns the supplied marking rubric
into a practical, student-friendly success map — one entry per rubric
criterion/outcome, with the rubric's own codes and terminology preserved,
never replaced by a generic taxonomy. It never writes the assignment or
tells Ammu what content to produce, and it never invents assessment
criteria when no rubric is supplied.

- Prompt: [`prompts/02_rubric_success_criteria.md`](prompts/02_rubric_success_criteria.md)
- Implementation: [`src/ammu_review/rubric_success_criteria.py`](src/ammu_review/rubric_success_criteria.py)
- Structured output model: `RubricSuccessCriteria` (`rubric_provided`,
  `criteria: list[RubricCriterion]`, `overall_top_band_profile`,
  `success_checklist`, `limitations`). Each `RubricCriterion` carries
  `code`, `name`, `teacher_wording`, `student_friendly_meaning`,
  `observable_evidence`, `top_band_requirements`, `good_vs_outstanding`,
  and `common_failure_modes`.

### Usage

```python
import asyncio
from ammu_review import review_assignment, review_rubric_success_criteria

async def main():
    understanding = await review_assignment(assignment=assignment_text, rubric=rubric_text)
    success_map = await review_rubric_success_criteria(
        assignment=assignment_text,
        rubric=rubric_text,                     # optional
        assignment_understanding=understanding,  # optional context, not authoritative
    )
    print(success_map.model_dump_json(indent=2))

asyncio.run(main())
```

## Stage 3: Student Work Review

Stage 1 answers "what is the task?"; Stage 2 answers "what does success look
like?"; Stage 3 answers "how well does Ammu's ACTUAL submitted work
currently demonstrate that?" It is a REVIEWER, not a writer: it never
rewrites her work or supplies a replacement sentence/paragraph, and it
prefers surfacing a question over stating a conclusion — see `.ai/PRODUCT.md`
"Guiding Principles" for the north star this follows. Output is deliberately
structured (discrete `issues` with stable ids, per-criterion
`rubric_assessment`) so the future Stage 4 ("Gap & Priority Review") has
concrete material to triage rather than free-text prose to re-parse.

- Prompt: [`prompts/03_student_work_review.md`](prompts/03_student_work_review.md)
- Implementation: [`src/ammu_review/student_work_review.py`](src/ammu_review/student_work_review.py)
- Structured output model: `StudentWorkReview` (`strengths`, `task_alignment`,
  `rubric_assessment: list[RubricAssessment]`, `evidence_reviews: list[EvidenceReview]`,
  `analysis_review: AnalysisReview` (WHAT/HOW/WHY/SO-WHAT), `issues: list[ReviewIssue]`,
  `limitations`). Each `ReviewIssue` gets a stable `id` (e.g. `S3-ISSUE-1`)
  assigned in Python after generation, not by the model, so it's guaranteed
  unique and deterministic for Stage 4 to reference.

### Usage

```python
import asyncio
from ammu_review import review_assignment, review_rubric_success_criteria, review_student_work

async def main():
    understanding = await review_assignment(assignment=assignment_text, rubric=rubric_text)
    success_map = await review_rubric_success_criteria(
        assignment=assignment_text, rubric=rubric_text, assignment_understanding=understanding
    )
    review = await review_student_work(
        assignment=assignment_text,
        student_work=student_draft_text,
        rubric=rubric_text,                       # optional
        assignment_understanding=understanding,   # optional context, not authoritative
        success_criteria=success_map,              # optional context, not authoritative
    )
    print(review.model_dump_json(indent=2))

asyncio.run(main())
```

Accuracy concerns are only raised when they can be established from the
supplied material itself (an internal contradiction, e.g. the work
disagreeing with a date stated in the task brief) — Stage 3 does not fact-check
general-knowledge claims against the real world, and does not use web
search. If a claim's accuracy can only be checked externally, it's surfaced
as something for Ammu to double-check herself, never as a confirmed
correction.

### Rubric Trajectory (additive capability)

Added onto Stage 3 without changing Stage 3 itself — a fully separate
function/model, not a new field on `StudentWorkReview`. It estimates where
Ammu's current work sits against the rubric, translated into an **estimated
grade trajectory** — explicitly not a prediction of the teacher's actual
mark, and never presented with false precision.

- Prompt: [`prompts/03b_rubric_trajectory.md`](prompts/03b_rubric_trajectory.md)
- Implementation: same file as Stage 3, [`src/ammu_review/student_work_review.py`](src/ammu_review/student_work_review.py)
- Structured output model: `RubricTrajectory` (`criteria: list[CriterionTrajectory]`
  with `estimated_score_percent`/`confidence`/`rationale`/`limitation` per
  criterion, `overall_estimated_score_percent`, `overall_confidence`,
  `biggest_opportunity`, `next_boundary_requirements`, `limitations`,
  `estimated_grade`, `grade_boundaries_used`).

**Grade boundaries are configurable, not hardcoded into the review logic.**
The model estimates a percentage; `grade_for_percent()` maps that to a
letter in plain Python, using `grade_boundaries` (default: A≥90, B≥70,
C≥50, D<50) passed into `review_rubric_trajectory()`. The model is
explicitly told not to compute or state a letter grade itself.

```python
import asyncio
from ammu_review import review_rubric_trajectory, grade_for_percent, DEFAULT_GRADE_BOUNDARIES

async def main():
    trajectory = await review_rubric_trajectory(
        assignment=assignment_text,
        student_work=student_draft_text,
        rubric=rubric_text,
        grade_boundaries=DEFAULT_GRADE_BOUNDARIES,  # pass your own scheme here
    )
    print(trajectory.model_dump_json(indent=2))

asyncio.run(main())
```

If the rubric doesn't give enough information to support a meaningful
percentage (no marks/weights, vague bands) — for a single criterion or
overall — that percentage is left unset and the specific reason is stated
in `limitations`/`limitation`, never filled with an invented number. If no
rubric is supplied at all, `criteria` is empty and `estimated_grade` is
`None`.

## Stage 4: Priority Coach

Stage 3 is the diagnostic reviewer ("what is wrong or missing?"); Stage 4
is the prioritizer/coach ("what should Ammu work on **first**?"). It does
not re-review the work — it takes Stage 3's issues and Rubric Trajectory's
position as input and makes one editorial decision: which single thing
matters most right now, explained in a way that challenges Ammu's thinking
rather than doing it for her. Design rationale is in
[`.ai/STAGE_4_PRIORITY_COACH_DESIGN.md`](.ai/STAGE_4_PRIORITY_COACH_DESIGN.md).

- Prompt: [`prompts/04_priority_coach.md`](prompts/04_priority_coach.md)
- Implementation: [`src/ammu_review/priority_coach.py`](src/ammu_review/priority_coach.py)
- Structured output model: `PriorityCoach` — `priority_issue_id` (a
  validated reference to a Stage 3 `ReviewIssue.id`, or `None`),
  `priority_statement`, `priority_category`, `why_this_matters`,
  `primary_criterion`/`also_affects_criteria: list[CriterionRef]`,
  `trajectory_connection`, `student_question`, `improvement_target`,
  `evidence_to_consider`, `other_issues_deferred`, `confidence`,
  `limitations`, plus `current_grade`/`target_grade` (both computed in
  Python, never by the model).

```python
import asyncio
from ammu_review import review_priority_coach

async def main():
    coach = await review_priority_coach(
        assignment=assignment_text,
        student_work=student_draft_text,
        rubric=rubric_text,                     # optional
        assignment_understanding=understanding,  # optional context, not authoritative
        success_criteria=success_map,             # optional context, not authoritative
        student_work_review=work_review,          # optional context -- issues to prioritize among
        rubric_trajectory=trajectory,             # optional context -- current grade position
    )
    print(coach.model_dump_json(indent=2))

asyncio.run(main())
```

**Priority-issue-id validation:** if the model references an issue id that
doesn't actually appear in the supplied `student_work_review.issues`, it's
discarded (set to `None`) and the mismatch is recorded in `limitations` —
a dangling/hallucinated id is never allowed to leak into the result, since
a future revision loop would need to trust `priority_issue_id` to check
whether that specific issue was later resolved. When the id *is* valid,
`priority_category` is overwritten from that issue's real category rather
than trusting the model's restatement of it.

**Grade-boundary framing is deterministic:** `current_grade` is read
directly from the supplied `RubricTrajectory.estimated_grade`, and
`target_grade` is computed by `next_grade_up()` — plain Python, using the
same `grade_boundaries_used` Rubric Trajectory already computed. The model
never calculates or invents a grade boundary; it only writes the
qualitative `trajectory_connection` explanation, using hedged language
("is likely to strengthen your position toward the X range"), never a
specific point/percentage claim.

## Stage 5: Toughest Teacher Review

This is the final planned review stage — after this, the review engine is
considered feature-complete (no more stages; the next phase is a
controlled pilot, not another stage). Stage 3 is the broad diagnostic
review; Stage 5 is one last adversarial check: *"if I were the toughest
reasonable teacher marking this against this rubric, what would I still
challenge before letting this work move into the next grade band?"* It
explicitly re-examines whether Stage 4's selected priority has actually
been addressed in the current work, challenges whether Rubric Trajectory's
current position is justified (in qualitative terms only, never inventing
a new percentage), and surfaces a small, ranked set (at most 3) of the
most significant remaining challenges — not a full re-review.

- Prompt: [`prompts/05_toughest_teacher.md`](prompts/05_toughest_teacher.md)
- Implementation: [`src/ammu_review/toughest_teacher.py`](src/ammu_review/toughest_teacher.py)
- Structured output model: `ToughestTeacherReview` — `overall_judgment`,
  `trajectory_challenge`, `priority_status` (`resolved` /
  `partially_resolved` / `unresolved`, or `None` if no Stage 4 priority was
  supplied), `priority_status_explanation`,
  `unresolved_issues: list[TeacherChallenge]` (ranked, each with a
  validated `issue_id`, `category`, `related_criteria`, `observation`,
  `why_it_matters`, `teacher_challenge`, `student_question`),
  `resolved_or_adequately_addressed`, `evidence_that_supports_judgment`,
  `what_would_change_my_mind`, `final_student_question`,
  `final_improvement_target`, `confidence`, `limitations`, plus
  `current_grade`/`priority_coach_issue_id` (both echoed in Python from
  upstream results, never invented by the model).

```python
import asyncio
from ammu_review import review_toughest_teacher

async def main():
    review = await review_toughest_teacher(
        assignment=assignment_text,
        student_work=student_draft_text,
        rubric=rubric_text,                       # optional
        assignment_understanding=understanding,   # optional context, not authoritative
        success_criteria=success_map,               # optional context, not authoritative
        student_work_review=work_review,            # optional context -- issues to check/reference
        rubric_trajectory=trajectory,               # optional context -- current position to challenge
        priority_coach=priority,                    # optional context -- the priority to check resolution of
    )
    print(review.model_dump_json(indent=2))

asyncio.run(main())
```

**Two Python-side safety nets, not prompt-only guardrails:**
- If no `priority_coach` was supplied, `priority_status` is forced to
  `None` regardless of what the model outputs — a model cannot actually
  know whether an unsupplied priority was resolved, so its claim is
  discarded and logged as a limitation. Every referenced Stage 3 issue id
  (in `unresolved_issues`) is validated the same way Stage 4 validates
  `priority_issue_id`: an id that doesn't match a real supplied issue is
  discarded and logged, and a valid id's `category` is overwritten from
  that issue's real category.
- Every question field (`final_student_question`, each
  `TeacherChallenge.student_question`) is checked for a trailing `?`, and
  every judgement-prose field is scanned for an invented percentage figure
  (Rubric Trajectory owns percentage estimation, not Stage 5) — violations
  are recorded in `limitations`, never silently rewritten, since rewriting
  the model's own text would itself be the system inventing content.

## Student Experience — Application Layer (Phase A) and Streamlit UI (Phase B)

The review engine (Stages 1–5) is frozen and consumed, never modified, by a
new application/session layer built on top of it: `src/ammu_review/app/`.
This is the layer described as "Application / Session Layer" in the Student
Experience design proposal, sitting between the UI and the engine.

- `app/models.py` — `Assignment` (one task/rubric/teacher_instructions
  triple, with Stage 1/2 output computed once) and `Draft` (one snapshot of
  the student's work plus everything computed for it), grouped into an
  `AssignmentSession`.
- `app/store.py` — `SessionStore`, one JSON file per assignment session on
  disk (base directory configurable via `AMMU_SESSIONS_DIR`, never
  hardcoded). Flat files are the simplest thing that works at pilot scale —
  no database ahead of an actual need.
- `app/orchestration.py` — `create_assignment()` (Stage 1 + 2, once per
  assignment), `submit_draft()` (Stage 3 → Rubric Trajectory → Stage 4 for
  each new draft), and `challenge_draft()` (Stage 5, on demand). Persists
  after every stage call so a crash mid-pipeline never loses an
  already-paid-for model call.
- `app/presentation.py` — pure functions translating Stage 1/2 structured
  output into plain, Grade-9-friendly dicts. No AI calls happen here; it's
  templating over already-computed fields, and it's how the UI avoids ever
  touching a Stage 1–5 field name or AI-vocabulary term directly.

**Previous-priority carry-forward** (`orchestration._resolve_priority_coach_for_challenge`):
`challenge_draft()` checks a *previous* draft's `PriorityCoach` against the
*current* draft's fresh Stage 3/Trajectory context, rather than the current
draft's own priority. That's what makes "did revising actually fix what I
told you to fix?" a real question Stage 5 can answer, using the existing
frozen `priority_coach` argument exactly as built — no new stage, no schema
change. The first draft in an assignment has nothing earlier to check, so it
falls back to checking its own priority. This is a lightweight substitute
for, not equivalent to, a future full revision-tracking loop that would
check every issue rather than just the one priority.

### Streamlit UI (`ui/app.py`)

Screens A (Assignment Setup) and B (Understand This Assignment) from the
Student Experience design proposal, run with:

```bash
uv run streamlit run ui/app.py
```

It's a thin presentation shell: every AI-generated value shown is routed
through `app/presentation.py` first, and the script never calls a Stage 1–5
function directly — only `ammu_review.app`'s orchestration functions.
Screens C–E (Your Review, Toughest Teacher Challenge, Reflection) are future
phases, not built yet.

### Tests

`tests/test_app_models.py`, `tests/test_app_store.py`,
`tests/test_app_presentation.py` run offline (no model calls).
`tests/test_app_orchestration.py` also runs offline, using a fake chat model
keyed by the requested structured-output schema so one fake model can drive
an entire multi-stage call — this is what verifies the previous-priority
carry-forward logic precisely (asserting which draft's `PriorityCoach` text
actually reached the Stage 5 prompt). `tests/test_ui_app_live.py` drives the
real `ui/app.py` script end-to-end via Streamlit's `AppTest`, using Ammu's
actual Hannah Clarke assignment/rubric and real model calls — skipped
automatically without `OPENAI_API_KEY`, like every other `*_live.py` file.

## Telemetry (Data / Telemetry Foundation)

A lightweight, append-only observer of the application layer, added to let
the first controlled student pilot answer questions like "did the student
revise?" and "was their priority resolved?" without changing the review
engine or the UI. Full design/rationale: [`.ai/TELEMETRY.md`](.ai/TELEMETRY.md).

- `src/ammu_review/telemetry/` — a package sibling to `app/`, not nested
  inside it: `models.py` (`EventType`, `TelemetryEvent`), `store.py`
  (`TelemetryStore`, append-only JSON Lines, one `<assignment_id>.jsonl`
  file per assignment, directory configurable via `AMMU_TELEMETRY_DIR`),
  `recorder.py` (`TelemetryRecorder`, the only API `app/orchestration.py`
  calls).
- `app/orchestration.py`'s `create_assignment()`/`submit_draft()`/
  `challenge_draft()` each take an optional `recorder` parameter (default
  `None` constructs a real one automatically, same pattern as `model=None`)
  and emit events at each meaningful step: `ASSIGNMENT_CREATED`,
  `ASSIGNMENT_UNDERSTOOD`, `DRAFT_SUBMITTED`, `REVISION_SUBMITTED`,
  `REVIEW_STARTED`, `REVIEW_COMPLETED`, `PRIORITY_SELECTED`,
  `PRIORITY_CHALLENGE_STARTED`, `PRIORITY_CHALLENGE_COMPLETED`.
- **A telemetry failure never breaks a review** — `TelemetryRecorder.record()`
  catches and logs any storage error internally; `orchestration.py` calls it
  unconditionally, with no surrounding try/except of its own.
- **Privacy**: no student name/email/school/teacher-name, no raw
  `assignment_text`/`student_work_text`, no full AI-generated prose — only
  ids, categories, counts, durations, and letter-grade estimates. See
  `.ai/TELEMETRY.md` "Privacy and data minimization" for the full list of
  what is and isn't captured, and what future consent/identity work a
  broader pilot would still need.
- `ui/app.py` is unmodified by this phase — it doesn't pass a `recorder`
  argument, so it gets real telemetry automatically via the default.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY

uv sync
```

Model configuration is environment-only (see `src/ammu_review/config.py` and
`.env.example`) — no credentials or model names are hard-coded. LangSmith
tracing is enabled automatically if you set the standard
`LANGSMITH_TRACING` / `LANGSMITH_API_KEY` variables; no code change is
needed either way.

## Running Stages 1–5

```bash
# Runs all five stages (plus Rubric Trajectory) against the sample
# assignment/rubric/work in data/
uv run python -m ammu_review

# Or against your own files
uv run python -m ammu_review path/to/assignment.md path/to/rubric.md path/to/student_work.md
```

This requires a valid `OPENAI_API_KEY` in `.env` since it makes real model
calls.

## Running the tests

```bash
uv run pytest -v
```

`test_assignment_understanding.py`, `test_rubric_success_criteria.py`,
`test_student_work_review.py`, `test_rubric_trajectory.py`,
`test_priority_coach.py`, and `test_toughest_teacher.py` run entirely
offline — they substitute a fake chat model, so no `OPENAI_API_KEY` or
network access is required. They check that the supplied text actually
reaches the model, that missing inputs are handled without error, and that
each prompt's own guardrails are intact. `test_rubric_trajectory.py` and
`test_priority_coach.py` also unit-test
`grade_for_percent()`/`next_grade_up()` directly (pure Python, no model at
all) to confirm grade boundaries are genuinely configurable and never
hardcoded. `test_priority_coach.py` and `test_toughest_teacher.py` verify
the Python-side safety net around Stage 3 issue-id references (a
hallucinated id is discarded and logged; a valid one's category overrides
the model's own restatement) — `test_toughest_teacher.py` additionally
verifies that `priority_status` is forced to `None` when no
`priority_coach` was supplied (regardless of what the model claims), the
question-format guardrail (`?`-ending, never silently rewritten), and the
no-invented-percentage guardrail across judgement prose.

The `*_live.py` counterparts call a real model, because what they check —
that the model actually grounds its output in the supplied material rather
than a generic taxonomy or invented content — is a property of real model
reasoning that a fake model can't exercise. They're skipped automatically
when `OPENAI_API_KEY` isn't set, so the rest of the suite stays runnable
offline anywhere, including CI. `test_student_work_review_live.py`,
`test_rubric_trajectory_live.py`, `test_priority_coach_live.py`, and
`test_toughest_teacher_live.py` each share one real pipeline run across
their tests via a module-scoped fixture, rather than re-running it per
test — `test_toughest_teacher_live.py`'s fixture is the most expensive one
yet (Stage 1 → 2 → 3 → Trajectory → 4 → 5, six chained model calls per
test-file run, not per test).

## Project layout

```
src/ammu_review/   Python package
prompts/            Prompt specs, one per review stage (separate from code)
data/               Sample assignment/rubric used by tests and the CLI
tests/              Test suite
docs/               Process templates (ADR, bug, feature, PR, sprint, retro)
.ai/                AI-agent working agreements (being updated for this stack)
```
