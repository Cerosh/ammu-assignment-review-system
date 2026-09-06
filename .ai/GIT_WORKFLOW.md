# GIT_WORKFLOW.md

# Git Workflow & Version Control Standards

Assignment Review System

Version: 1.0

Owner: Cerosh Jacob

Last Updated: 2026-07-06

---

# Purpose

This document defines the Git workflow for the Assignment Review System.

Its goals are to:

- Maintain a clean Git history
- Support safe collaboration
- Enable reliable releases
- Simplify rollbacks
- Provide consistency for both developers and AI assistants

Git history should tell the story of how the product evolved.

---

# Core Principles

Every commit should:

- Solve one logical problem
- Be easy to understand
- Be easy to review
- Be easy to revert
- Build successfully

Avoid mixing unrelated work into the same commit.

---

# Branch Strategy

## Main Branch

`main`

Purpose

- Production-ready code
- Protected branch
- Always deployable

Rules

- No direct commits
- Changes only through Pull Requests
- CI must pass
- Code review required

---

## Feature Branches

Pattern

feature/<short-description>

Examples

feature/submission-list

feature/search

feature/dashboard-redesign

feature/seo-improvements

Rules

- One feature per branch
- Keep branches short-lived
- Rebase frequently if needed

---

## Bug Fix Branches

Pattern

bugfix/<short-description>

Examples

bugfix/mobile-navigation

bugfix/search-filter

bugfix/card-layout

---

## Hotfix Branches

Pattern

hotfix/<short-description>

Purpose

Urgent production issues.

Examples

hotfix/homepage-crash

hotfix/security-header

Rules

- Small, focused changes
- Highest priority
- Merge back into `main` immediately after review

---

## Release Branches (Optional)

Pattern

release/<version>

Examples

release/1.0.0

release/1.1.0

release/2.0.0

Purpose

Final validation before production.

Use only if the release process becomes more complex.

---

# Branch Naming Rules

Use:

- Lowercase
- Hyphens
- Short, descriptive names

Avoid:

feature/new-feature-final-final

bugfix/test

temp

my-branch

---

# Daily Workflow

1. Pull the latest changes from `main`.
2. Create a feature branch.
3. Implement one logical change.
4. Commit frequently with meaningful messages.
5. Push the branch.
6. Open a Pull Request.
7. Address review feedback.
8. Merge after approval.
9. Delete the feature branch.

---

# Commit Philosophy

Each commit should represent one meaningful step.

A reviewer should understand the purpose by reading:

- Commit message
- Diff

---

# Commit Message Format

Use Conventional Commits.

Format

type(scope): short description

Examples

feat(review): add submission status filtering

feat(search): implement keyword search

fix(homepage): correct hero layout on mobile

docs(ai): update CLAUDE.md guidance

refactor(repository): simplify data access

test(directory): add Playwright search tests

chore(deps): update dependencies

---

# Allowed Commit Types

feat

New functionality.

fix

Bug fixes.

docs

Documentation only.

style

Formatting only.

refactor

Code improvement without behaviour change.

perf

Performance improvements.

test

Tests.

build

Build configuration.

ci

CI/CD changes.

chore

Maintenance.

revert

Undo a previous commit.

---

# Commit Rules

Keep commits:

- Small
- Focused
- Reviewable

Avoid committing:

- Unrelated changes
- Temporary debugging
- Commented-out code
- Unused files

Every commit should leave the project in a working state.

---

# Doc-Staleness Guardrails

Automated Husky hooks (`scripts/validate-*.ts`) that catch specific documentation-staleness
patterns: stale "not yet shipped" claims in text being committed right now, sprint docs left
untouched by code that references them, and sprint status/consistency drift.

`.husky/pre-commit` (fails the commit, no escape hatch — this is a file-internal consistency
check, not a judgement call):

- **Sprint doc consistency** (`npm run validate:sprint-consistency`) — if a sprint's `README.md`
  Features table is 100% "Completed," that sprint's `tasks.md` must have zero unchecked boxes.

`.husky/commit-msg` (fails the commit; bypass with a `Docs-Deferred: <reason>` trailer in the
commit message — visible in `git log`, not a silent `--no-verify` skip):

- **No self-contradiction** (`npm run validate:no-contradiction`) — blocks "not yet
  committed/deployed"-style text if it appears in lines this commit is adding. `scripts/**` is
  exempt (the pattern list itself legitimately contains these phrases).
- **Sprint doc contact** (`npm run validate:sprint-doc-contact`) — if the commit message references
  a sprint (e.g. "Sprint 11", "Sprint 09b") and touches `app/`, `components/`, `features/`, or
  `lib/`, at least one file under that sprint's own `sprints/sprint-NN-*/` folder must be part of
  the same commit. Only applies once commit messages consistently include a "(Sprint NN)"
  reference — adopt that convention before relying on this check.
- **Doc freshness** (`npm run validate:doc-freshness`) — if a commit adds a "Sprint Status:
  ...Complete/Deployed" line to a sprint's `README.md`, `.ai/CONTEXT.md` must be part of the same
  commit.

Run `npm run validate:docs` to check staged changes against all of the above ad hoc, before
committing. In CI, the same checks run against the push/PR's full commit range
(`.github/workflows/ci.yml`).

---

# Pull Request Standards

Every Pull Request should include:

## Summary

What changed?

Why was it needed?

---

## Scope

Which features or areas are affected?

---

## Testing

How was the change validated?

Examples

- Manual testing
- Unit tests
- Playwright
- Responsive testing

---

## Screenshots

Include before/after screenshots for UI changes.

---

## Risks

Document any known risks or limitations.

---

## Documentation

Confirm whether documentation was updated.

---

# Pull Request Checklist

Before requesting review:

- [ ] Builds successfully
- [ ] TypeScript passes
- [ ] ESLint passes
- [ ] Tests pass
- [ ] Responsive verification completed
- [ ] Accessibility reviewed
- [ ] Documentation updated
- [ ] No debug code
- [ ] No console logging left behind
- [ ] Commit history is clean

---

# Review Workflow

Reviewer should verify:

- Requirements met
- Architecture respected
- Naming consistency
- Readability
- Performance
- Accessibility
- Security
- Documentation

Refer to REVIEW_CHECKLIST.md.

---

# Merge Strategy

Preferred

Squash and Merge

Benefits

- Clean history
- One commit per feature
- Easier rollback

Avoid merge commits unless there is a clear reason.

---

# Rebase Guidelines

Use rebase to:

- Keep feature branches current
- Reduce merge conflicts

Do not rewrite published history that others depend on.

---

# Tags

Tag every production release.

Examples

v1.0.0

v1.1.0

v2.0.0

Tags should correspond to released versions.

---

# Changelog

Maintain CHANGELOG.md.

Every release should document:

- Features
- Improvements
- Bug fixes
- Breaking changes

Do not rewrite historical entries.

---

# Git Ignore

Ensure `.gitignore` excludes:

- node_modules
- .next
- dist
- coverage
- .env.local
- .env.*
- IDE settings (where appropriate)
- OS-specific files
- Build artefacts

Commit only source code and required configuration.

---

# Large Files

Avoid committing:

- Videos
- Archives
- Large images
- Generated files

Use external storage if necessary.

Optimise assets before committing.

---

# AI Development Workflow

When using Claude Code:

1. Create a feature branch before implementation.
2. Keep AI tasks focused on one objective.
3. Review all generated code.
4. Never commit code that is not understood.
5. Request a code review before merging.
6. Ask Claude to recommend a Conventional Commit message.

AI assists development but does not replace engineering judgement.

---

# Emergency Fixes

For production incidents:

1. Create a hotfix branch.
2. Implement the smallest safe fix.
3. Review the change.
4. Deploy.
5. Verify production.
6. Merge the hotfix back into `main`.
7. Update documentation if required.

---

# Repository Hygiene

Regularly:

- Delete merged branches
- Update dependencies
- Archive obsolete code
- Remove unused assets
- Keep documentation current

A clean repository is easier to maintain.

---

# Definition of a Good Commit

A good commit:

- Solves one problem
- Has a clear message
- Builds successfully
- Is easy to review
- Is easy to revert
- Improves the project

---

# Definition of a Good Pull Request

A good Pull Request:

- Has a clear purpose
- Is appropriately sized
- Includes testing evidence
- Includes updated documentation
- Receives thoughtful review
- Leaves the project better than it was before

---

# Guiding Principle

Git is more than a backup system.

It is the engineering history of the project.

Every branch, commit and Pull Request should help future developers understand not only what changed, but why it changed.