# Production Readiness

Baseline assessment (PR-1). This is inspection and documentation only — no
application behavior was changed to produce this document.

## 1. Current Architecture

This is a single-process Python application, not a web/API service in the
Next.js sense. Everything runs inside one Streamlit process:

```
Browser (Streamlit's own JS/WebSocket client)
  <-> Streamlit server process (ui/app.py, `streamlit run`)
        -> Application layer (src/ammu_review/app/): models, SessionStore,
           orchestration.py, presentation.py
             -> Review engine, Stages 1-5 (frozen), one real OpenAI call
                per stage via langchain-openai's ChatOpenAI
             -> Telemetry (src/ammu_review/telemetry/), observer-only
        -> Local filesystem: data/sessions/*.json, data/telemetry/*.jsonl
```

There is no separate frontend framework, no API server, and no database.
`ui/app.py` is a thin Streamlit shell: it never calls a Stage 1-5 function
directly and never renders anything not passed through
`ammu_review.app.presentation` first.

A second, unrelated tree exists at `_archive/nextjs-scaffold/` — a
committed-but-inert Next.js/Vercel project scaffold (its own `package.json`,
`vercel.json`, Playwright/Husky config, and a GitHub Actions workflow under
`_archive/nextjs-scaffold/.github/workflows/`). It predates this project's
actual Streamlit/Python direction. Confirmed inert: there is no top-level
`.github/` directory, so GitHub Actions never discovers or runs that nested
workflow, and nothing in `pyproject.toml`/`uv.lock`/the app imports anything
from it.

**Important finding:** `.ai/DEPLOYMENT.md` and `.ai/SECURITY.md` are also
leftovers from that same generic scaffold/template set — they describe a
Next.js + Vercel + Supabase static-website architecture ("Version 1 is a
static website", "Current Framework: Next.js 15", RBAC roles like
"Submitter"/"Moderator") that has nothing to do with this codebase. They do
not reflect this project's actual architecture and were not used as a
source of truth for this document. They should not be treated as
authoritative until rewritten or clearly marked historical (see Section 5,
P2).

## 2. Current Deployment Model

**A. Entry point:** `uv run streamlit run ui/app.py` (documented in
`README.md`). A secondary CLI entry point, `uv run python -m ammu_review`
(`src/ammu_review/__main__.py`), runs Stages 1-5 against files on disk with
no UI — useful for engineering/debugging, not part of the student
experience.

**B. Frontend:** Streamlit only. Not React/Next.js, not a hybrid — the only
Next.js material in the repo is the inert archived scaffold above.

**C. Where the Python app runs:** wherever `streamlit run` is invoked —
today, only a developer's local machine. No hosting is currently
configured.

**D. Session storage:** `src/ammu_review/app/store.py`'s `SessionStore`
writes one JSON file per assignment to `data/sessions/`, a plain local
directory. The path is overridable via `AMMU_SESSIONS_DIR`; the default
resolves relative to the repo (`.../data/sessions`). Both `data/sessions/`
and `data/telemetry/` are in `.gitignore`.

**E. Telemetry storage:** `src/ammu_review/telemetry/store.py`'s
`TelemetryStore` writes one append-only JSON Lines file per assignment to
`data/telemetry/`, same configurable-directory pattern via
`AMMU_TELEMETRY_DIR`. Directory-creation failure at this path is now caught
inside `TelemetryRecorder.__init__` (see the just-completed fix) rather than
crashing the caller.

**F. OpenAI API key:** `src/ammu_review/config.py` calls `load_dotenv()`
and reads `OPENAI_API_KEY` implicitly — `ChatOpenAI(...)` picks it up from
the environment itself; no code ever reads or stores the key value.
Locally it's supplied via a `.env` file loaded by `python-dotenv`.

**G. Hardcoded secrets:** none found in tracked source. A repo-wide grep
for API-key-shaped strings and `api_key = "..."` literals across `*.py` and
`*.md` (excluding `.env*`) returned nothing. The local `.env` (gitignored,
confirmed via `git log --all -- .env` to have never been tracked/committed)
does contain real, live credentials (`OPENAI_API_KEY`, `TAVILY_API_KEY`,
`LANGSMITH_API_KEY`) — this is expected local-development configuration,
not a repository exposure, but it's worth the operator's awareness that
these are live keys sitting in plaintext on disk locally.

**H. Writable filesystem requirement:** yes, unconditionally. Both
`SessionStore` and `TelemetryStore` call `mkdir(parents=True, exist_ok=True)`
and write files at runtime. There is no in-memory or database-backed
alternative today.

**I. Single process / single user assumption:** yes, clearly. `ui/app.py`
caches one `SessionStore` instance per server process via
`@st.cache_resource`, and `SessionStore.list_assignment_ids()` is used
directly to populate a "Resume an assignment" dropdown in the sidebar —
**every visitor to the running app sees every assignment ID ever created on
that instance and can open any of them.** There is no user concept, no
login, no per-user partitioning anywhere in the application or data model.
This is the single biggest architectural fact shaping the pilot
recommendation below (see Section 5, P0).

**J. Vercel-specific files:** none in the live application. The only
Vercel-related file in the repo is `_archive/nextjs-scaffold/vercel.json`,
part of the inert archived scaffold.

**K. Can this be deployed to Vercel without architectural changes?** No.
See Section 4.

**L. Simplest reliable hosting for this architecture:** a small persistent
host that runs `streamlit run` as a long-lived process with a real,
persistent disk/volume mounted at the session/telemetry directory. See
Section 3.

## 3. Pilot Deployment Recommendation

Goal, verbatim from the brief: "Ammu should be able to access the
application remotely and use it for one or more real school assignments."
That is a single-user (or very small, known set of users), low-traffic,
low-concurrency workload where losing her review history to a
filesystem reset would be a real (if recoverable-by-resubmitting) loss.
Reliability of *persistence* matters more than scale here.

**Recommended: a small container/VM host with a persistent volume,
running the existing `streamlit run ui/app.py` process unchanged** — e.g.
Render, Railway, or Fly.io (any of these work equally well; pick whichever
the operator already has an account with). Concretely this means:

- One long-running web service, build command `uv sync`, start command
  `uv run streamlit run ui/app.py --server.port $PORT --server.address
  0.0.0.0` (the port/address flags are the only concession the current code
  needs — no application code change).
- A persistent volume mounted at the directory pointed to by
  `AMMU_SESSIONS_DIR` / `AMMU_TELEMETRY_DIR`, so `data/sessions/` and
  `data/telemetry/` survive restarts and redeploys.
- `OPENAI_API_KEY` (and optionally `AMMU_MODEL_NAME`, `LANGSMITH_*`) set as
  that platform's environment variables/secrets, never in the repo.

**Streamlit Community Cloud** was also considered — it's the most
frictionless option (free, connects directly to the GitHub repo, has a
built-in secrets manager) and would work for a brief demo. It is **not**
recommended as the primary pilot host because its filesystem is not
guaranteed persistent across app reboots/redeploys/inactivity-sleep — an
idle-timeout wake or a redeploy could silently reset `data/sessions/` and
`data/telemetry/`, quietly deleting Ammu's actual assignment history. It's
a reasonable fallback for a throwaway demo, not for real assignment data
the pilot is meant to preserve.

## 4. Vercel Assessment

**Not appropriate for the current implementation, and not recommended.**
Two independent, architectural (not incidental) mismatches:

1. **Runtime model.** Streamlit is a long-running, stateful Python process
   that holds a persistent WebSocket connection per browser session and
   re-executes the whole script top-to-bottom on every interaction. Vercel
   serverless/edge functions are short-lived, stateless, request-scoped
   invocations with no persistent WebSocket support and no guaranteed warm
   process between requests. There is no way to run `streamlit run` as a
   Vercel function without rewriting the entire UI in a framework Vercel
   natively supports (Next.js, etc.) — which the brief explicitly rules
   out ("Do not rebuild the UI just to use Vercel").
2. **Filesystem.** Vercel's function filesystem is ephemeral and read-only
   outside `/tmp`, and `/tmp` itself doesn't persist across invocations or
   instances. `SessionStore`/`TelemetryStore` both require a durable,
   shared, writable directory across every request for the same
   assignment — structurally incompatible with Vercel's storage model
   without introducing an external database/object store, which is also
   out of scope for this PR.

Vercel would only become viable after a genuine rearchitecture (a real
frontend framework calling a stateless API layer backed by an external
database) — a different, much larger project, not a configuration change.
For this application as it exists today, a persistent-process host (Section
3) is the correct and much simpler choice.

## 5. Production Blockers

### P0 — Before Ammu

1. ~~**No access control.**~~ **Resolved in PR-2.** A private-pilot passcode
   gate (`src/ammu_review/pilot_access.py`, wired into `ui/app.py::main()`)
   now blocks the entire application entry point — no screen renders and
   no orchestration/telemetry/OpenAI call is reachable — until the correct
   `AMMU_PILOT_ACCESS_CODE` is entered for that browser session. See
   Section 10.
2. **No session/data isolation.** `store.list_assignment_ids()` is shown to
   every visitor in the sidebar "Resume an assignment" dropdown — any
   visitor who reaches the app can open *any* assignment ever created on
   that instance, including another user's draft text and review results.
   This is a genuine child-data exposure risk once the app is reachable by
   more than one person. PR-2's access gate limits *who can reach the app
   at all*, which is sufficient for a single-user (Ammu-only) pilot, but
   does not add per-user partitioning — that remains a real limitation if
   a second student is ever added (see P2, item 11).
3. **Filesystem persistence must be a deliberate hosting choice.** An
   ephemeral or ephemeral-on-idle host (e.g. most serverless platforms, or
   free tiers that reset local disk) would silently lose Ammu's session and
   telemetry files. The chosen host must mount a real persistent volume at
   the session/telemetry directories (Section 3).
4. **Secrets must come from the host's environment/secrets mechanism.**
   `OPENAI_API_KEY` is currently supplied only via a local `.env`; the
   deployed host must set it as a platform secret, and `.env` must never be
   committed or baked into a deploy artifact (already gitignored — verify
   this stays true on whichever host is chosen). PR-2 adds a fail-fast,
   presence-only check (`config.is_openai_api_key_configured()`) so a
   missing key now shows a safe, generic error instead of a raw
   construction error — see Section 10. The host must also set
   `AMMU_PILOT_ACCESS_CODE` (new in PR-2) as a platform secret.

### P1 — Before an external pilot beyond Ammu

5. **Unhandled exceptions surface as raw Streamlit tracebacks.** Nothing in
   `ui/app.py` wraps its `_run(...)` calls to `create_assignment`/
   `submit_draft`/`challenge_draft` in a try/except — an OpenAI failure
   (rate limit, network error, missing key) would currently show a raw
   Python stack trace to the student rather than a friendly message. Not a
   secret-exposure risk (no secret value is ever interpolated into an
   exception anywhere in the codebase — verified by reading
   `config.py`/`store.py`/`recorder.py`), but not acceptable UX for a
   child user in a real pilot.
6. **No rate limiting or cost cap**, per-session or global, on top of the
   access gate. One authenticated user could still generate unbounded API
   spend by repeatedly submitting drafts. Worth a soft cap before widening
   beyond a single trusted user.
7. **Streamlit production hardening not yet configured.** No
   `.streamlit/config.toml` exists; Streamlit's default error-detail and
   anonymous-usage-stats behavior has not been reviewed or explicitly set
   for a production/child-facing deployment.
8. **No operational log visibility confirmed.** Telemetry failures log at
   `WARNING` via Python's stdlib `logging` module with no configured
   handler/sink — whatever host is chosen must be confirmed to actually
   capture and surface process stdout/stderr, or these warnings go nowhere
   an operator will ever see.
9. **No data retention/deletion policy** for session or telemetry files —
   already flagged as future work in `.ai/TELEMETRY.md`'s own "Future
   privacy work required" section; still open, and matters more once real
   student data lives on a hosted disk rather than a developer's laptop.

### P2 — Later

10. `_archive/nextjs-scaffold/` and the generic, currently-inaccurate
    `.ai/DEPLOYMENT.md` / `.ai/SECURITY.md` (and similarly templated files
    like `.ai/GIT_WORKFLOW.md`) are stale scaffold artifacts from an
    unrelated project template. They're inert today but already misled
    this exact inspection task on first read — worth pruning or clearly
    marking historical so a future reader (human or AI) doesn't mistake
    them for this project's real deployment/security posture.
11. True multi-user session isolation (per-student data partitioning, not
    just a shared access passcode) — appropriate to defer while the pilot
    is Ammu alone, necessary before a second student is added.
12. Token/cost accounting telemetry (already documented as deferred in
    `.ai/TELEMETRY.md`).
13. Health-check endpoint, structured monitoring/alerting.

## 6. Security and Privacy Findings

All findings below are repository-grounded (grep/read/git-log verified),
not theoretical:

- No hardcoded secrets in any tracked `.py` or `.md` file (repo-wide grep
  for key-shaped strings and `api_key = "..."` literals returned nothing
  outside `.env*`, which is itself gitignored and confirmed never
  committed).
- No raw `assignment_text` or `student_work_text` ever reaches telemetry —
  enforced by `TelemetryRecorder`/`app/orchestration.py`'s design and
  covered by an existing test,
  `tests/test_app_orchestration_telemetry.py::test_no_raw_student_work_text_appears_in_any_event`.
- No PII fields exist anywhere in the data model at all — `Assignment`,
  `Draft`, `AssignmentSession`, and `TelemetryEvent` (in
  `app/models.py`/`telemetry/models.py`) have no name/email/school/teacher
  field to accidentally populate; there's nothing to leak because it was
  never modeled in the first place.
- No secret value is ever string-interpolated into a log message or raised
  exception anywhere in `config.py`, `store.py` (session or telemetry), or
  `recorder.py` — confirmed by reading each file directly.
- **The clearest real privacy gap is architectural, not a coding
  mistake:** zero session isolation (Section 5, P0 #2). This is the finding
  that matters most for a child user and is the direct motivation for
  PR-2's access gate.
- The local `.env` contains live, real API keys (OpenAI, Tavily,
  LangSmith) in plaintext — normal for local dev, flagged here only so the
  operator is aware these are real credentials, not placeholders, sitting
  on this machine's disk.

## 7. Cost Protection Findings

- Exactly three call sites trigger any OpenAI call: `create_assignment()`
  (Stage 1 + Stage 2), `submit_draft()` (Stage 3 + Rubric Trajectory +
  Stage 4), and `challenge_draft()` (Stage 5) — all in
  `src/ammu_review/app/orchestration.py`.
- Every one of these is invoked from `ui/app.py` only behind an explicit
  `st.button(...)`, each disabled while its input text is empty
  (`disabled=not assignment_text.strip()`, etc.) — nothing calls a review
  function automatically on page load or on an unrelated rerun.
- **Stage 5 gating verified directly in code, not assumed:**
  `render_toughest_teacher_screen` only renders the "Challenge my work"
  button inside the `if draft.toughest_teacher_review is None:` branch —
  gated on *persisted* state on the `Draft` object, not `session_state`, so
  it cannot be silently re-triggered by a page refresh or a new browser
  session; once a challenge review exists, the button to create another
  one for that draft is never shown again.
- No rate limiting, per-IP/per-session throttling, or budget cap exists
  anywhere in the codebase today. Combined with the "no access control"
  finding (Section 5, P0 #1), an undeployed-behind-a-gate instance is an
  unmetered cost-generating endpoint for anyone who finds the URL — the
  concrete reason PR-2's access gate is a P0, not a nice-to-have.

## 8. Deployment Checklist

For the next implementation phase (deployment itself, not part of PR-1/2):

- [ ] Choose a persistent-process host with a mountable volume (Render,
      Railway, Fly.io, or similar) — not Vercel, not a filesystem-ephemeral
      free tier.
- [ ] Set `OPENAI_API_KEY` (and optionally `AMMU_MODEL_NAME`, `LANGSMITH_*`)
      as that host's environment variables/secrets — never in the repo or
      build image.
- [ ] Mount a persistent volume at `AMMU_SESSIONS_DIR` and
      `AMMU_TELEMETRY_DIR` (set both explicitly rather than relying on the
      package-relative default).
- [ ] Set the PR-2 pilot access secret as a host environment variable.
- [ ] Confirm the host captures process stdout/stderr so telemetry-failure
      warnings are actually visible somewhere.
- [ ] Start command: `uv sync && uv run streamlit run ui/app.py
      --server.port $PORT --server.address 0.0.0.0` (adjust flags to the
      host's port-injection convention).
- [ ] Smoke-test after first deploy: create an assignment, submit a draft,
      restart/redeploy the service, confirm the assignment is still listed
      (proves the volume mount is real, not just configured).
- [ ] Revisit P1 items (Section 5) before inviting anyone beyond Ammu.

## 9. Explicitly Deferred

Not part of PR-1, PR-2, or this baseline — intentionally out of scope for
now:

- Authentication system (real user accounts, OAuth/SSO, password reset).
- Parent dashboard.
- Teacher dashboard.
- Learning profile / long-term student model.
- LangGraph or any multi-agent architecture.
- Database migration (flat-file JSON/JSONL remains appropriate at this
  scale).
- Full analytics platform (telemetry stays JSON Lines files, per
  `.ai/TELEMETRY.md`).
- Major UI redesign.
- Enterprise security architecture (RBAC, audit logging, SSO, etc.).
- Actual deployment/hosting execution — this document recommends an
  approach; it does not stand up any infrastructure.

## 10. PR-2 Implementation: Pilot Access & Configuration

Implemented since the baseline above was written — resolves P0 items #1 and
part of #4 (Section 5).

**Secrets/configuration approach.** No new settings framework was
introduced. `src/ammu_review/config.py` (existing) gained one small,
additive function, `is_openai_api_key_configured()` — a presence-only check
(no real API call) letting `ui/app.py` fail fast with a safe, generic
message rather than a raw construction error surfacing from inside
`ChatOpenAI` when the key is missing. A new sibling module,
`src/ammu_review/pilot_access.py`, holds the pilot-access secret reader
(`get_pilot_access_code()`) and a constant-time comparison
(`check_access_code()`, via `hmac.compare_digest`). Neither function
caches or logs the values it reads.

**Required environment variables.**
- `OPENAI_API_KEY` — required (unchanged from before PR-2).
- `AMMU_PILOT_ACCESS_CODE` — new, required in any deployed environment. An
  empty string is treated identically to unset (fails closed), so an
  accidentally-blank platform secret can't silently disable the gate.
- `AMMU_MODEL_NAME`, `AMMU_SESSIONS_DIR`, `AMMU_TELEMETRY_DIR`,
  `LANGSMITH_*` — unchanged, all still optional.

**Pilot access mechanism.** A single shared passcode, entered once per
browser session on a plain "Private Pilot" screen
(`render_access_gate()` in `ui/app.py`), rendered and checked *before*
`main()` does anything else — before `get_store()`, before any
session-state routing, before any Stage 1-5 or telemetry call is reachable.
On success, `st.session_state.pilot_authenticated = True` is set (kept only
in that browser session's in-memory Streamlit state, never written to a
session file, never logged) and the entered code is immediately popped out
of `session_state` so it doesn't linger any longer than necessary. This is
a controlled-pilot gate, not a user-account system — there is still no
concept of "a student" in the data model, and everyone who has the one
shared code sees the same session-isolation behavior already documented in
Section 5, P0 #2 (unchanged by this PR).

**Fail-closed behavior**, all three cases now covered explicitly:
- Access code unconfigured → `st.error` with a generic message, `st.stop()`
  — the "Private Pilot" form itself never renders, and nothing past it is
  reachable.
- Access code configured, wrong/no code entered → gate stays up,
  `st.error("That code isn't right. Try again.")`, `pilot_authenticated`
  never gets set.
- `OPENAI_API_KEY` unconfigured (checked only after authentication) →
  same generic `st.error` + `st.stop()` pattern, no configuration detail or
  stack trace shown.

**Privacy considerations.** No new PII was introduced — the access code is
a shared operational secret, not tied to any student identity. It is never
persisted (no session file, no telemetry event, no log line references it,
per `tests/test_pilot_access.py`'s logging test and the pop-after-use
behavior above) and never appears in a URL (it's a Streamlit widget value
over the app's own session state, not a query parameter). `.env.example`
now documents `AMMU_PILOT_ACCESS_CODE` as a placeholder-only entry,
consistent with `OPENAI_API_KEY`'s existing treatment there.

**Intentionally not implemented in PR-2:** user accounts of any kind,
per-user data partitioning (still the P0 #2 gap noted in Section 5),
rate limiting/cost caps (still P1 #6), and any change to Stage 1-5,
`app/orchestration.py`, `app/models.py`, `app/presentation.py`, or the
telemetry package — none of those files were touched by this PR.

**Tests added:** `tests/test_pilot_access.py` (9 tests — pure logic: env
read, fail-closed on unset/empty, constant-time comparison correctness,
never-logged, `.env.example` placeholder-only) and
`tests/test_ui_pilot_access.py` (7 tests — Streamlit `AppTest`-level
boundary tests: gate blocks/allows/rejects correctly, fails closed with no
code configured, unauthenticated sessions never construct a `SessionStore`
or reach a review-triggering widget, authenticated sessions reach the
existing Screen A unchanged, missing `OPENAI_API_KEY` fails gracefully
post-authentication). All 21 pre-existing offline UI tests across
`tests/test_ui_screen_c.py`, `tests/test_ui_screen_d.py`,
`tests/test_ui_app_live.py`, `tests/test_ui_screen_c_live.py`, and
`tests/test_ui_screen_d_live.py` were updated to prime
`at.session_state["pilot_authenticated"] = True` before their first
`.run()` — the minimal change required so the new gate doesn't block tests
that were written to exercise Screens A-D directly, per this project's own
"do not fix/refactor unrelated things" convention (no other line in any of
those files changed).

**Regression:** full suite, 210 passed (194 before PR-2, +16 new pilot
access tests), one clean run, no code-related flake.

## 11. PR-3 — Deployment + Runtime Safety

### Deployment recommendation

Unchanged from Section 3's baseline recommendation, re-confirmed rather
than re-litigated: a small persistent-process host (Render, Railway, Fly.io
— any works, pick whichever the operator already has an account with)
running `uv sync && uv run streamlit run ui/app.py --server.port $PORT
--server.address 0.0.0.0` as a single long-lived web service, with a
persistent volume mounted at `AMMU_SESSIONS_DIR`/`AMMU_TELEMETRY_DIR`.
Nothing in this inspection changed that conclusion — the application is
still a single Streamlit process requiring a writable filesystem, and
still structurally incompatible with Vercel for the same two reasons as
before (stateful long-running process, no persistent writable storage on
Vercel's serverless functions). `.streamlit/config.toml` (new in PR-3) now
carries the small, non-secret Streamlit-level hardening this recommendation
assumed: `client.showErrorDetails = false` (never show a raw traceback if
one somehow reaches Streamlit's own error handling, on top of `ui/app.py`'s
own `_run()` safety net below), `browser.gatherUsageStats = false`
(disable Streamlit's own anonymous usage stats, separate from this
project's telemetry, unnecessary for a child user), and `server.headless =
true` (required by non-interactive hosts; harmless locally). Port/address
binding is deliberately left to the host's own start command, not hardcoded
here, since different hosts inject `$PORT` differently.

### Required environment variables

| Variable | Required? | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | Required | Read automatically by `ChatOpenAI`; app fails safely (generic message, no stack trace) if missing, via `config.is_openai_api_key_configured()` (PR-2). |
| `AMMU_PILOT_ACCESS_CODE` | Required in any deployed environment | The private-pilot passcode gate (PR-2). Fails closed if unset. |
| `AMMU_SESSIONS_DIR` | Should be set explicitly in deployment | Where session JSON files are written. Defaults to a path relative to the repo — fine locally, **wrong in any deployed environment** unless it points at a mounted persistent volume (see "Filesystem persistence" below). |
| `AMMU_TELEMETRY_DIR` | Should be set explicitly in deployment | Same as above, for telemetry JSON Lines files. |
| `AMMU_MAX_DRAFTS_PER_ASSIGNMENT` | Optional | New in PR-3 — caps draft/revision submissions per assignment (see "Cost protection" below). Default 10 is generous; only set this to something else deliberately. |
| `AMMU_MODEL_NAME` | Optional | Overrides the default model. |
| `LANGSMITH_*` | Optional | Standard LangChain tracing variables, unrelated to this app's own telemetry. |

Verified directly in code, not assumed: `config.py`'s `load_dotenv()` +
`os.getenv` reads, `pilot_access.py`'s `os.getenv`, `app/store.py` and
`telemetry/store.py`'s `os.getenv(..., DEFAULT_..._DIR)` fallback pattern,
and `cost_guard.py`'s `os.getenv` (new in PR-3) all read straight from the
environment with no other configuration path — nothing here was assumed.

### Filesystem persistence

Both `SessionStore` and `TelemetryStore` call `self.base_dir.mkdir(parents=True,
exist_ok=True)` in `__init__` and write plain files with no locking:
`SessionStore.save()` does a full-file `write_text()` (last write wins);
`TelemetryStore.append()` opens in append mode and writes one JSON line
per event. Directories are created on first use, not at import time, so
deployment doesn't need to pre-create them — but it does need the process
to have write access to wherever `AMMU_SESSIONS_DIR`/`AMMU_TELEMETRY_DIR`
point.

**What survives a restart:** whatever the hosting platform's filesystem
guarantees. If the chosen host provides a real persistent volume mounted
at those paths, everything survives process restarts and redeploys. If it
doesn't (an ephemeral or reset-on-redeploy filesystem — see Section 3's
Streamlit Community Cloud caveat), **all of Ammu's session and telemetry
data for every assignment is lost** on the next restart, with no warning
to her and no way to recover it. This is not a database — there is no
backup, no replication, no recovery path. Deploying this app on any host
without confirming persistent storage would be deploying it in a way that
can silently erase a real student's real work.

**Restart/redeploy behavior**, precisely: on process start, both stores
just `mkdir` (a no-op if the directory already exists) — an existing
directory's files are read normally on next access, an absent one starts
empty. There is no migration step, no schema versioning, nothing that
could fail on restart beyond the directory/file permissions already
covered above.

**Two processes writing the same files:** not a concern for this pilot.
The recommended deployment (Section 3) is a single long-running process,
single replica — there is no multi-worker/multi-instance configuration
here, and nothing in `SessionStore`/`TelemetryStore` uses file locking
because nothing currently requires it. This would become a real risk only
if the app were ever scaled to multiple concurrent replicas sharing one
volume (a last-write-wins race on `SessionStore.save()`, or interleaved
appends on `TelemetryStore.append()`) — explicitly out of scope for a
single-student pilot, and not implemented here per the brief's instruction
not to add file locking without a concrete issue. Documented as a known
limitation (below), not fixed.

### Runtime failure handling

**Before this PR:** none of `ui/app.py`'s four call sites into the
application layer (`create_assignment`, `submit_draft` ×2, `challenge_draft`)
were wrapped in any error handling — a real OpenAI failure (network error,
timeout, rate limit, an auth/configuration error, or any other model/API
exception) would propagate all the way up through Streamlit's own script
runner and render as a raw Python traceback in the browser. Confirmed by
reading `ui/app.py` directly before making any change, not assumed.

**Now:** every one of those four call sites is wrapped by a single shared
helper, `_run(coro, action)` in `ui/app.py`, which:
- Catches any `Exception` from the awaited call (this deliberately covers
  the whole realistic failure surface listed above — network failure,
  timeout, API unavailable, rate limit, authentication/configuration
  error, and any other unexpected model/API exception — with one generic
  handler, rather than trying to enumerate and special-case each one).
- Shows the student one plain, friendly message: "Something went wrong
  getting your review. Please try again in a moment -- if it keeps
  happening, let your teacher or the app owner know." No traceback, no
  internal detail, ever.
- Logs `"<action> failed (<ExceptionTypeName>)."` at `WARNING` via Python's
  standard `logging` module — enough for an operator to know *what*
  failed and *roughly why* (the exception class), without logging the
  exception's message or a full traceback. This is a deliberate choice:
  some API client libraries echo request details (e.g. a masked API key
  fragment) back into their exception's message text, so keeping the log
  to type-name-only avoids that risk entirely rather than trying to
  sanitise every possible library's message format.
- Returns `None` on failure. Every call site checks for `None` and returns
  immediately rather than touching an attribute of a missing result (which
  would itself raise an `AttributeError` and defeat the whole point) —
  this leaves the student on the same screen, with the same inputs still
  in their widgets where Streamlit preserves them, free to just try again.

**What this does NOT fix**, documented rather than solved (out of scope —
would require touching `app/orchestration.py`, which is frozen for this
PR): if a multi-stage call fails *partway through* (e.g. Stage 3 succeeds
and gets persisted, then Stage 3b throws), the partially-completed draft
is saved but there is no UI affordance to retry just the remaining stages
for that specific draft — the student would need to submit a new
draft/revision to get a fresh attempt. Rare in practice (this requires a
failure mid-pipeline, not before or after it), and the resulting partial
state renders gracefully rather than crashing (Screen C's presentation
functions already handle `None` fields — verified by existing
`test_app_presentation_screen_c.py` coverage), so the pilot is safe to run
with this documented rather than fixed.

### Cost protection

**Verified directly from the code, not assumed**, exactly how many model
calls each action costs and what already prevents runaway repetition:

| Action | Model calls | Existing protection |
|---|---|---|
| A. Create assignment | 2 (Stage 1, Stage 2) | None beyond requiring the student to re-type the assignment/rubric text each time — a much weaker "accidental repeat" risk than a single button. |
| B. Submit first draft | 3 (Stage 3, Rubric Trajectory, Stage 4) | New in PR-3: `AMMU_MAX_DRAFTS_PER_ASSIGNMENT` guard (below). |
| C. Submit a revision | 3 (same three stages) | Same guard as B — both paths call the same `submit_draft()`, and both are now guarded identically. |
| D. Press "Toughest Teacher" | 1 (Stage 5) | Already existed, reconfirmed by re-reading `ui/app.py::render_toughest_teacher_screen`: the "Challenge my work" button only renders `if draft.toughest_teacher_review is None`, gated on **persisted** draft state, not `session_state` — it cannot run twice for the same draft even across a full browser restart. No new guard needed or added here. |
| E. Rerunning Streamlit (a widget interaction elsewhere on the page) | 0 | Every review-triggering call is behind an explicit `if st.button(...)`, which is `True` only on the exact rerun triggered by that click and `False` on every other rerun — confirmed by reading every call site; nothing runs on an unrelated widget interaction. |
| F. Refreshing/reopening the browser | 0 | A real browser reload starts a brand-new Streamlit session with fresh `session_state` (`assignment_id`/`draft_id` reset to `None`), landing back on Screen A — no call happens automatically; the student would need to click through again from a clean state. |

**New guard added:** `src/ammu_review/cost_guard.py`. Protects exactly one
operation — submitting a draft or revision for review (`submit_draft`,
actions B and C above; each "operation" is one submission, regardless of
whether it's the first draft or a later revision, since both cost the
same 3 calls and both are reachable repeatedly via "back to assignment
overview" → resubmit). Default limit: 10 drafts per assignment,
configurable via `AMMU_MAX_DRAFTS_PER_ASSIGNMENT`; a non-positive or
non-numeric configured value falls back to the default rather than
disabling the guard. When the limit is reached, `ui/app.py` shows a
`st.warning(...)` in place of the draft/revision text area and submit
button entirely (so the action is structurally unavailable, not just
declined after the fact), naming no internal configuration beyond the
limit number itself. Reaching the limit never touches, recomputes, or
invalidates any already-completed draft/review — it only blocks
submitting one more.

**Why 10 is sufficient for the pilot:** the intended workflow is
understand → draft → maybe revise once or twice → optionally challenge.
Genuine use rarely exceeds 2-3 submissions per assignment; 10 leaves
generous headroom for a thorough student without meaningfully capping
normal work, while still stopping an accidental rapid-repeat-click or a
runaway script well short of real cost. Stage 5 needed no equivalent new
guard (see table above) and assignment creation wasn't guarded for the
reason in the table's first row — both are documented conclusions from
inspecting the existing code, not gaps.

**Deliberately not implemented:** precise token/cost accounting. As
`.ai/TELEMETRY.md` already documents, obtaining real per-call token/dollar
figures would mean either modifying the frozen Stage 1-5 functions to
extract usage metadata (out of scope) or a deeper LangChain callback
integration not designed here. A simple operation count is preferable to
an inaccurate dollar estimate at this stage, per this PR's own brief.

### Streamlit rerun safety (verified, not changed)

Inspected specifically for: does a browser refresh, an unrelated widget
interaction, or a partially-completed session ever trigger a duplicate
expensive call? Conclusion for all three: no, and nothing needed fixing.
- Refresh: new session, fresh `session_state`, lands on Screen A — no call
  fires without an explicit click (see table row F above).
- Unrelated reruns: every expensive call is behind `if st.button(...)`,
  which Streamlit guarantees is `True` only on its own triggering rerun.
- Partial session: covered under "Runtime failure handling" above — a
  half-completed draft renders gracefully rather than duplicating a call,
  it just has no in-place retry affordance (documented limitation, not a
  duplicate-call risk).

Access control (PR-2) is unaffected: `render_access_gate()` still runs
first in `main()`, before `get_store()` or any screen routing, and none of
this PR's changes touch that ordering.

### Health / availability

No health-check endpoint was added. The recommended hosts (Render,
Railway, Fly.io) determine health by whether the process is listening on
the injected `$PORT` and responding to HTTP — which a running Streamlit
server already does at its normal root path. A dedicated `/healthz`-style
endpoint is unnecessary complexity for this deployment size and wasn't
added, per the brief's explicit instruction not to add one enterprise
platforms happen to expect if the actual chosen host doesn't need it.

### Deployment checklist

Manual steps for the next (deployment) phase — this PR does not perform
any of these:

1. Provision the host (Render/Railway/Fly.io), pointed at this repo.
2. Set environment variables/secrets on the host: `OPENAI_API_KEY`,
   `AMMU_PILOT_ACCESS_CODE`, `AMMU_SESSIONS_DIR`, `AMMU_TELEMETRY_DIR`
   (pointed at the mounted volume path), optionally `AMMU_MODEL_NAME` /
   `AMMU_MAX_DRAFTS_PER_ASSIGNMENT` / `LANGSMITH_*`.
3. Mount a real persistent volume at the `AMMU_SESSIONS_DIR`/
   `AMMU_TELEMETRY_DIR` path.
4. Start command: `uv sync && uv run streamlit run ui/app.py --server.port
   $PORT --server.address 0.0.0.0`.
5. Work through the manual smoke test below.
6. Restart/redeploy once, then re-check that an assignment created before
   the restart is still listed — this is the one check that actually
   proves the volume mount is real, not just configured.

### Manual deployment smoke test

Work through this by hand against the deployed URL — not an automated
browser test, a checklist for a human:

1. Application starts (the host reports the service healthy/running).
2. Opening the URL shows the "Private Pilot" gate, not the app itself.
3. An invalid access code is rejected and the gate stays up.
4. The correct access code grants access and shows Screen A.
5. An assignment can be created (paste task + rubric, submit).
6. Assignment understanding (Screen B, top half) renders.
7. Rubric/success-criteria processing (Screen B, bottom half) renders.
8. A draft can be submitted.
9. The review completes (Screen C renders fully).
10. The priority ("Your biggest opportunity") appears.
11. A revision can be submitted and produces a fresh review.
12. "Toughest Teacher" (Screen D) runs and shows a verdict.
13. Telemetry continues working (a `.jsonl` file appears for the
    assignment under the configured `AMMU_TELEMETRY_DIR`, with no raw
    assignment/student text in it).
14. Temporarily unset `OPENAI_API_KEY` on the host and confirm the app
    fails with the safe "isn't set up yet" message, not a stack trace —
    then restore it.
15. Temporarily unset `AMMU_PILOT_ACCESS_CODE` and confirm the app fails
    closed (same safe message, gate never appears) — then restore it.
16. Trigger a real API failure if practical (e.g. a temporarily invalid
    key) and confirm the student sees the generic "something went wrong"
    message, never a traceback — then restore the real key.
17. Check the host's logs and the browser's page source/network tab for
    the access code or API key — confirm neither ever appears.

### Known limitations

Not hidden, listed plainly:

- **Shared pilot access code** — one passcode for everyone who has it, not
  per-user accounts. Fine for a single trusted pilot user; not a
  multi-user identity system.
- **No per-user data isolation** — the sidebar "Resume an assignment" list
  shows every assignment on the instance to anyone who has the pilot code
  (documented since PR-1, unchanged by PR-2/PR-3's access gate, which
  controls *who can reach the app*, not *what they can see once in*).
- **Local filesystem persistence, no durable database** — session/telemetry
  data survives only as long as the hosting platform's filesystem does;
  see "Filesystem persistence" above for exactly what's at risk.
- **No enterprise rate limiting** — `AMMU_MAX_DRAFTS_PER_ASSIGNMENT` is a
  simple, generous, single-operation guard against accidental runaway
  usage, not a real quota/billing system.
- **No precise token/cost accounting** — `model_call_count` (existing
  telemetry) and the new draft-count guard are both call-count proxies,
  not dollar figures.
- **No in-place retry for a mid-pipeline partial failure** — see "Runtime
  failure handling" above; a new draft/revision submission is the
  student's recovery path today.
- **Two-process file-write races** — not a risk at single-replica scale
  (the recommended deployment), but would become one if ever scaled to
  multiple concurrent instances sharing one volume without adding file
  locking or a real datastore first.
