# Telemetry

## Status

V0.1 — the telemetry foundation described here is implemented. It captures
technical/system-side events from the application layer only. No
student-facing interaction events (e.g. "the student looked at their
priority") exist yet — those are deferred to Screen C/E, see "Deferred to
Screen C/E" below.

## Purpose

Telemetry exists to let us learn from the first controlled student pilot,
answering questions like: what did the student do, what did the system
tell them, did they act on it, and did it actually help. It is
**observational, not authoritative** — the `AssignmentSession`/`Draft`
objects in `ammu_review.app` remain the source of truth for what actually
happened; telemetry is a lightweight, disposable record of the journey
around them, not a second copy of the data.

## Architecture

`src/ammu_review/telemetry/` is a package sibling to `app/`, not nested
inside it — it observes the application layer rather than being part of
what the application does:

- `models.py` — `EventType` (the vocabulary) and `TelemetryEvent` (the
  schema).
- `store.py` — `TelemetryStore`, append-only JSON Lines, one
  `<assignment_id>.jsonl` file per assignment.
- `recorder.py` — `TelemetryRecorder.record(...)`, the only API
  `app/orchestration.py` calls. Catches and logs any storage failure
  internally — see "Failure isolation" below.

**Dependency direction is one-way and enforced by import structure:**

```
UI (ui/app.py)
  -> Application layer (ammu_review.app)
       -> Review engine (Stages 1-5, frozen)
       -> Telemetry (ammu_review.telemetry)   <- observer only
```

`ammu_review.telemetry` never imports from `assignment_understanding.py`,
`rubric_success_criteria.py`, `student_work_review.py`, `priority_coach.py`,
or `toughest_teacher.py`, and none of those files import telemetry. The
only integration point is `app/orchestration.py`.

## Event schema

```
TelemetryEvent
    event_id: str        # auto-generated, unique per event
    event_type: EventType
    timestamp: datetime  # UTC
    session_id: str       # currently always == assignment_id, see below
    assignment_id: str
    draft_id: str | None  # present for draft/review/challenge events
    metadata: dict         # event-specific, structured, non-identifying
```

**Why `session_id` always equals `assignment_id` today:** an
`AssignmentSession` is 1:1 with an `Assignment` in the current application
layer — there is no separate "session" concept yet (no login, no
multi-device continuation). `session_id` is kept as its own field for
forward compatibility, not because it currently carries different
information.

## Event catalogue

Emitted today, from `app/orchestration.py`:

| Event | Emitted from | Metadata |
|---|---|---|
| `ASSIGNMENT_CREATED` | `create_assignment()`, after Stage 1 | — |
| `ASSIGNMENT_UNDERSTOOD` | `create_assignment()`, after Stage 2 | `rubric_provided` |
| `DRAFT_SUBMITTED` | `submit_draft()`, on every submission | `draft_number`, `word_count` |
| `REVISION_SUBMITTED` | `submit_draft()`, only when `draft_number > 1` (in addition to `DRAFT_SUBMITTED`) | `previous_draft_id`, `new_draft_id`, `draft_number` |
| `REVIEW_STARTED` | `submit_draft()`, before Stage 3 | — |
| `REVIEW_COMPLETED` | `submit_draft()`, after Stage 3 → Rubric Trajectory → Stage 4 | `success`, `duration_ms`, and on success: `stages_completed`, `model_call_count`, `issue_count`, `limitation_count`; on failure: `error_type` |
| `PRIORITY_SELECTED` | `submit_draft()`, after Stage 4 succeeds | `priority_issue_id`, `priority_category`, `criterion_code`, `current_grade`, `target_grade` |
| `PRIORITY_CHALLENGE_STARTED` | `challenge_draft()`, before Stage 5 | `priority_coach_source_draft_id` (which draft's priority is being checked — see the carry-forward note below) |
| `PRIORITY_CHALLENGE_COMPLETED` | `challenge_draft()`, after Stage 5 | `success`, `duration_ms`, and on success: `previous_priority_issue_id`, `priority_status`, `current_grade`, `trajectory_changed`; on failure: `error_type` |

**Reserved, not yet emitted** (defined in `EventType` for a stable
vocabulary, no code path produces them today):

| Event | Why it's deferred |
|---|---|
| `PRIORITY_VIEWED` | Requires a UI interaction event from Screen C ("student looked at their priority") — Screen C doesn't exist yet. |
| `REFLECTION_SAVED` | Requires the Reflection screen (E) and a reflection-persistence field, neither of which exist yet. |
| `SESSION_STARTED` | Would be redundant with `ASSIGNMENT_CREATED` given `session_id == assignment_id` today; kept in case a genuinely separate session concept (e.g. resuming across devices) is introduced later. |
| `SESSION_COMPLETED` | No "mark this assignment finished" action exists in the application layer yet. |

### Deferred to Screen C/E

When Screen C (Your Review) is built, it should emit `PRIORITY_VIEWED` when
the student actually opens/expands the priority (not just on page load), and
`PRIORITY_CHALLENGE_STARTED`/`COMPLETED` already fire correctly for the
"challenge me" action since that's fully implemented in `challenge_draft()`.
When the Reflection screen (E) is built, `REFLECTION_SAVED` should fire with
`reflection_present=true` and `reflection_length` — never the reflection
text itself.

## Failure isolation

A telemetry failure must never break an assignment review — telemetry is
observational, the review is not. `TelemetryRecorder.record()` catches any
exception from the underlying store and logs it via Python's `logging`
module at `WARNING` level; it never raises. `app/orchestration.py` therefore
calls `recorder.record(...)` unconditionally, with no surrounding
try/except of its own. Verified by
`tests/test_app_orchestration_telemetry.py::test_telemetry_failure_does_not_break_submit_draft`,
which injects a store whose `append()` always raises and confirms
`submit_draft()` still returns a fully-populated `Draft`.

A *real* stage failure (e.g. the model call itself raises) is different: it
is a genuine application error and is recorded (`REVIEW_COMPLETED`/
`PRIORITY_CHALLENGE_COMPLETED` with `success: false`) and then re-raised,
never swallowed.

## Persistence

JSON Lines, one `<assignment_id>.jsonl` file per assignment, written
append-only under a configurable base directory:

```bash
export AMMU_TELEMETRY_DIR=/path/to/telemetry   # optional, defaults to data/telemetry/
```

This mirrors `ammu_review.app.store.SessionStore`'s existing
`AMMU_SESSIONS_DIR` convention. One file per assignment means a single
student's whole journey for that assignment is readable top to bottom, in
emission order, with no query engine required — appropriate for a small
pilot; a proper analytics backend is an explicit future extension, not
built here.

## Privacy and data minimization

**What telemetry stores:** event ids, event types, timestamps, assignment/
draft ids (already-anonymous, randomly-generated identifiers with no link
to a real name), word counts, issue/criterion codes, categories, letter
grade estimates, durations, success/failure flags, and error type names.

**What telemetry intentionally does NOT store:**
- Student name, email, phone number, address, school name, or teacher name.
- Any authentication or credential information.
- Raw `assignment_text` or `student_work_text` — the actual content lives
  only in `AssignmentSession`/`Draft`, which telemetry references by id and
  never duplicates. `tests/test_app_orchestration_telemetry.py::test_no_raw_student_work_text_appears_in_any_event`
  verifies a distinctive marker placed in submitted draft text never
  reaches an emitted event.
- Full AI-generated prose (observations, judgments, strengths) — only
  references (ids, categories, counts) that let metrics be computed without
  re-reading the content.

**How student identity is currently represented:** it isn't. There is no
concept of a "student" or "user" anywhere in this system yet — only an
anonymous, randomly-generated `Assignment`/`Draft` id per submission, with
no login and no link back to a real person. Telemetry inherits this: an
event references an assignment/draft id and nothing else identifying.

**Future privacy work required before a broader pilot:** a lightweight
pseudonymous participant/student identifier, an explicit consent flow, and
a data-retention/deletion policy. None of this is implemented in this
phase — authentication and consent management were explicitly out of scope
here.

## Product metrics this event model enables (not built yet)

The event model is designed so these can be computed later from stored
events, without any new instrumentation:

1. Review completion rate — `REVIEW_STARTED` vs `REVIEW_COMPLETED(success=true)`.
2. Priority engagement rate — `PRIORITY_SELECTED` vs future `PRIORITY_VIEWED`.
3. Revision rate — assignments with a `REVISION_SUBMITTED` event.
4. Priority resolution rate — `PRIORITY_CHALLENGE_COMPLETED.priority_status == "resolved"`.
5. Trajectory improvement rate — `PRIORITY_CHALLENGE_COMPLETED.trajectory_changed`.
6. Toughest Teacher challenge rate — assignments with any `PRIORITY_CHALLENGE_STARTED`.
7. Student reflection rate — future `REFLECTION_SAVED` presence.
8. Student-reported usefulness — not yet designed; needs a UI interaction event once that concept exists.
9. Average review latency — `REVIEW_COMPLETED.duration_ms`.
10. Model/API failure rate — `REVIEW_COMPLETED.success == false` / `PRIORITY_CHALLENGE_COMPLETED.success == false`, grouped by `error_type`.
11. Review cost per assignment — `model_call_count` gives a call-count proxy today; real token/cost accounting is deferred (see below).

**Critical journey this enables reconstructing** — draft → priority →
revision → priority resolution — without any new AI mechanism, purely from
existing events read from one assignment's `.jsonl` file in order:

```
DRAFT_SUBMITTED (draft_number=1)
  -> REVIEW_COMPLETED (success=true)
  -> PRIORITY_SELECTED (priority_issue_id=S3-ISSUE-2)
  -> DRAFT_SUBMITTED (draft_number=2) + REVISION_SUBMITTED
  -> REVIEW_COMPLETED (success=true)
  -> PRIORITY_SELECTED (draft 2's own fresh priority)
  -> PRIORITY_CHALLENGE_STARTED (priority_coach_source_draft_id=<draft 1's id>)
  -> PRIORITY_CHALLENGE_COMPLETED (priority_status="resolved")
```

## Deferred: token/cost accounting

Real per-call token usage and dollar cost are not captured. Obtaining them
would require either (a) modifying the frozen Stage 1–5 functions to
extract usage metadata from each `ainvoke()` response, which the "do not
modify Stage 1–5" constraint for this phase rules out, or (b) reaching into
LangChain's callback/usage-tracking API from the application layer in a way
that isn't yet designed. LangSmith tracing (already configurable via the
standard `LANGSMITH_*` env vars, see `config.py`) already captures this
information per-call for engineering debugging purposes today.
`REVIEW_COMPLETED.model_call_count` (always 3 for a successful
Stage3→Trajectory→Stage4 chain, since none of those functions retry) is
included now as a free, deterministic proxy for review cost, without
touching the frozen engine. Real cost/token telemetry is a documented
future extension, not built in this phase.

## Future extensions

- Student-interaction events from Screen C/E (`PRIORITY_VIEWED`,
  `REFLECTION_SAVED`, and any new events those screens' actions need).
- Token/cost accounting (see above).
- A proper analytics backend once pilot scale outgrows JSON Lines files.
- Pseudonymous student identity + consent flow, required before a broader
  (non-controlled) pilot.
