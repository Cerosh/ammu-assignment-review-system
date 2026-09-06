# CLAUDE.md

# AI Engineering Constitution

Version: 1.0

Owner: Cerosh Jacob

---

# About the Project

Read PROJECT.md before starting any implementation.

Read ARCHITECTURE.md before making structural changes.

Read TODO.md before implementing features.

Read DECISIONS.md before changing existing patterns.

Never assume requirements.

If something is ambiguous, explain the ambiguity and propose options.

---

# Product Principles (Decision Framework)

Adopted 2026-09-06. Full context in `PRODUCT.md` "Guiding Principles" --
read that section, this is the short version to apply while implementing.

North star: build an AI that helps Ammu become better at producing
high-quality assignments herself.

Core rule: Ammu owns the work. The system owns the challenge.

When a design or implementation choice has two paths, prefer the one that
builds Ammu's own capability over the one that just produces output faster:

- AI doing the work -> AI improving Ammu's thinking.
- Giving her an answer -> asking the right question.
- Fixing one assignment -> building a transferable skill.
- Optimising for marks -> optimising for learning that leads to better marks.

This already governs Stage 1/2's refusal to write content or invent rubric
criteria, and their preference for self-check questions over instructions.
Apply the same test to every future stage, prompt, schema field, or UI
decision: does this choice make Ammu better at doing this herself, or does
it just do it for her?

---

# Development Workflow

Before writing code

Always

Understand the task.

Review affected files.

Identify reusable components.

Identify possible impacts.

Explain the implementation plan.

Then implement.

After implementation

Review your own code.

Look for:

- duplicated code
- unnecessary complexity
- performance issues
- accessibility
- security
- readability

Then suggest improvements.

---

# Architecture Rules

Never hardcode business data.

Always load from the repository layer.

Data source (JSON, a database, etc.) is TBD — see PROJECT.md/ARCHITECTURE.md.

UI components must never know where data comes from.

Separate:

Presentation

Business Logic

Data

Utilities

Types

---

# React Standards

Prefer:

Server Components

Use Client Components only when required.

Avoid unnecessary useEffect.

Avoid unnecessary useState.

Prefer derived state.

Prefer async Server Components.

Use Suspense where appropriate.

Keep rendering predictable.

---

# Folder Structure

Respect the existing architecture.

Do not create folders unless justified.

Prefer feature organization over large utility folders.

Avoid dumping files into lib.

---

# Naming Conventions

Use descriptive names.

Avoid abbreviations.

Good

BusinessCard

CommunityHero

SearchFilters

Bad

Card2

DataHelper

Utils

---

# Design Philosophy

Design should feel

Modern

Premium

Minimal

Clear

Think

Apple

Airbnb

Linear

Notion

Avoid clutter.

Whitespace is a feature.

---

# Git Workflow

Recommend a commit message after completing each task.

Use Conventional Commits.

Examples

feat:

fix:

docs:

refactor:

perf:

test:

style:

chore:

---

# Verification Handoff (cost-aware)

Established 2026-08-02, after discussing Claude Code token cost with the project owner.

For routine, binary checks after completing an implementation, hand verification to the project
owner instead of running it yourself:

- Report the exact commands to run: `npm run typecheck`, `npm run lint`, `npm run test` (full
  suite). Ask the owner to run them and report back pass, or paste the failure output if any.
- Don't ask to see raw output when the owner reports a pass — a clean self-report is sufficient
  for these three. Only ask for raw output if the result is a failure or ambiguous.
- Once confirmed clean, provide a suggested commit message (Conventional Commits, per Git
  Workflow above) for the owner to commit themselves, unless they ask you to commit.

This does **not** apply to CI/CD, deployment, or infrastructure verification (GitHub Actions
runs, Vercel deploys, env vars, secrets, live-site checks) — keep running those yourself,
directly. Self-reports are more likely to miss real bugs in that category (a stale deployment
snapshot, a silently-broken env var) than direct inspection would catch. Infra verification stays
hands-on regardless of cost, unless the owner explicitly asks otherwise.

## Local Quality Gates vs. CI

If something is only ever caught in CI — never locally, no matter what the developer ran by
hand — that's a gap in the local git hooks, not bad luck. Treat "CI caught it, local didn't" as a
prompt to check whether the failing category of check (typecheck, lint, unit tests, data
validation, doc consistency) is actually wired into `.husky/pre-commit` or `.husky/pre-push`, and
add it if not. Finding out via CI is slow (a full pipeline run) compared to a hook (seconds);
every category of check should run at the earliest hook that's cheap enough for it:

- `.husky/pre-commit`: fast checks only (lint-staged, typecheck, the unit test suite, data/doc
  validation scripts) — all of it should complete in a few seconds.
- `.husky/pre-push`: slower checks (e.g. the e2e/Playwright suite) that would make every commit
  sluggish if run pre-commit instead.

Example failure mode: a unit test failure only ever shows up in CI even though local checks were
run first — because `pre-commit` runs typecheck but not the unit suite, and `pre-push` runs only
e2e, not the unit suite either. If the unit suite runs in under a second, it belongs in
`pre-commit`. When CI catches something local didn't, ask *why* local didn't, don't just fix the
one failure and move on.

---

# When Unsure

Do not guess.

Explain assumptions.

Offer alternatives.

Recommend the simplest option.

Timing question (implement now vs. track for a future sprint) is separate from the spec-first
requirement below, and is usually already answered by how the project owner asks — a direct
instruction ("add X", "swap these two") means now. See Spec-Driven Development for what "now"
actually requires before code is written.

---

# Spec-Driven Development (Strict)

Adopted after prior projects saw real changes (a UI tweak, a section reorder, a new data field)
implemented directly from chat requests and only documented in sprint notes afterward — accurate,
but not spec-first. The project owner prefers full strictness with no exceptions over a lighter
content-vs-code threshold.

**No code is written — not even a one-line content edit — until a spec for it exists and has been
confirmed.** This applies equally to:

- A new feature or architectural change (e.g. a new API integration).
- A UI change (a lightbox, a reordered section, a new card).
- A pure content/data change (adding a business's email, editing a description).

There are no exceptions for "this is too small to need a spec."

## The four steps, every time

1. **Capture.** Before writing any code, add or update a Feature entry in the active sprint's
   `README.md` Features table: an ID (`F-XXX`), a one-line description, a priority, and explicit
   Acceptance Criteria — the same shape `docs/sprint-template.md` already defines. If no sprint is
   currently active/appropriate for the change, say so and ask which sprint it belongs to (or
   whether a new one is needed) rather than picking one unilaterally.
2. **Confirm.** State the spec back to the project owner (quote the Acceptance Criteria) and get an
   explicit go-ahead before implementing. When the project owner's own request already contains
   full acceptance-criteria-level detail, capturing it verbatim as a Feature entry and confirming
   "I've logged this as F-XXX with your exact criteria — implementing now" in the same turn is
   sufficient — the requirement is that the spec is written down before code starts, not that
   every change needs a separate round-trip of back-and-forth.
3. **Implement.** Build against the confirmed Acceptance Criteria only — nothing extra, nothing
   assumed.
4. **Verify and check off.** Mark each Acceptance Criterion complete only once actually
   verified (tested, observed running) — not just written or coded.

## Correction protocol

If reality diverges from the spec during implementation (a real API returns different data than
assumed, a library doesn't support what the spec assumed) — stop, update the spec/Acceptance
Criteria to reflect the correction, flag the change explicitly, and only then continue. Never
silently code around a stale spec, and never leave the spec and the shipped behaviour disagreeing
with each other.

## Model delegation for the Implement step

Capture, Confirm, and Verify all require judgment (scoping, ambiguity resolution, and honest
verification) and should run on the primary model. For a Feature whose Confirm step is already
complete — spec and Acceptance Criteria fully settled — and whose Implement step is genuinely
mechanical (no content decisions left, just executing an agreed change), delegating the Implement
step to a smaller/cheaper subagent under `.claude/agents/` is fine. That subagent's job is strictly
to make the already-agreed change and run the relevant validation — it must not make any content
decision (wording, structure, values) on its own. Local hooks and CI remain the safety net
regardless of which model did the write. This does not apply to Features that touch application
architecture, schema, or core logic — those stay on the primary model end to end.

---

# Templates & Playbook

Use these when the situation calls for them — they are not optional extras:

- Filing or investigating a bug: use `docs/bug-template.md`.
- Scoping a new feature: use `docs/feature-template.md`.
- Opening a Pull Request: use `docs/pr-template.md`.
- Recording an architectural decision: use `docs/adr-template.md`, then add it to DECISIONS.md.
- Running or documenting a meeting: use `docs/meeting-notes.md`.
- Closing a sprint or reviewing a release: use `docs/retrospective.md`.
- Planning a new sprint: use `docs/sprint-template.md` (the basis for every `sprints/sprint-XX-*/` folder).

For common recurring tasks (starting a session, building the current sprint, code/security/accessibility/performance review, refactors, TypeScript/ESLint fixes, ending a sprint), use the ready-made prompts in `PROMPT_PLAYBOOK.md` instead of writing a prompt from scratch.

---
