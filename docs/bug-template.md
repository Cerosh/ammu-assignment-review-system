# Bug Template

Assignment Review System

Bug ID:

Title:

Status:

Priority:

Severity:

Reported By:

Assigned To:

Sprint:

Target Release:

Date Reported:

Last Updated:

---

# Summary

Provide a short description of the issue.

Example

The search bar returns no results when searching by business category.

---

# Bug Type

Select one.

- Functional
- UI
- UX
- Accessibility
- Performance
- Security
- Data
- SEO
- Build
- Deployment
- Regression
- Documentation

---

# Severity

Choose one.

Critical

High

Medium

Low

Informational

---

# Priority

Choose one.

P0

P1

P2

P3

P4

---

# Status

Choose one.

Open

Investigating

In Progress

Blocked

Ready for Review

Testing

Resolved

Closed

Won't Fix

Duplicate

---

# Business Impact

Describe how users are affected.

Examples

Users cannot search businesses.

Homepage becomes unusable.

Mobile users cannot navigate.

Minor visual issue only.

---

# Environment

Environment

Development

Preview

Production

Operating System

Browser

Device

Screen Size

Application Version

Commit Hash

---

# Preconditions

Describe anything required before reproducing the issue.

Example

Business directory contains at least one plumbing business.

---

# Steps to Reproduce

1.

2.

3.

4.

5.

---

# Expected Behaviour

Describe what should happen.

---

# Actual Behaviour

Describe what actually happens.

---

# Screenshots

Attach screenshots or screen recordings if available.

Include browser console errors where helpful.

---

# Error Messages

Record any errors.

Example

```
TypeError: Cannot read properties of undefined
```

---

# Console Output

Paste relevant logs.

Avoid including sensitive information.

---

# Network Requests

If applicable

Request

Response

Status Code

Timing

---

# Root Cause Analysis

Leave blank until investigation is complete.

Questions

What caused the issue?

Why did it occur?

Why was it not detected earlier?

---

# Affected Components

Example

SearchBar

BusinessRepository

BusinessCard

Header

Footer

JSON Schema

---

# Related Features

Reference any affected feature documents.

Example

features/search.md

features/business-directory.md

---

# Related ADRs

List any Architecture Decision Records that may be relevant.

Example

ADR-0002

ADR-0005

---

# Proposed Solution

Describe the preferred fix.

Focus on the simplest safe solution.

Avoid unnecessary refactoring.

---

# Alternatives Considered

Option 1

Option 2

Option 3

Explain why alternatives were not selected.

---

# Risks

Potential risks introduced by the fix.

Examples

Regression

Performance

Accessibility

Data migration

Deployment

---

# Testing Plan

Unit Tests

- [ ]

Integration Tests

- [ ]

Playwright Tests

- [ ]

Manual Testing

- [ ]

Responsive Testing

- [ ]

Accessibility Testing

- [ ]

Regression Testing

- [ ]

Reference:

TESTING.md

---

# Regression Risk

Choose one.

Low

Medium

High

Describe why.

---

# Acceptance Criteria

- [ ] Root cause identified.
- [ ] Bug fixed.
- [ ] Tests updated.
- [ ] No regression introduced.
- [ ] Documentation updated if required.
- [ ] Verified in target environment.

---

# Documentation Updates

Update if required.

- [ ] CONTEXT.md
- [ ] TODO.md
- [ ] CHANGELOG.md
- [ ] DECISIONS.md
- [ ] TESTING.md

---

# AI Investigation Instructions

Before proposing a fix:

Read:

- CLAUDE.md
- ARCHITECTURE.md
- CODING_STANDARDS.md
- TESTING.md

During investigation:

- Reproduce the issue.
- Identify the root cause.
- Avoid guessing.
- Confirm the smallest safe fix.
- Consider edge cases.
- Check for similar issues elsewhere.

After implementing the fix:

- Run linting.
- Run TypeScript.
- Run relevant tests.
- Add or update automated tests.
- Suggest a Conventional Commit message.

---

# Resolution Summary

Describe what changed.

Why did it fix the issue?

---

# Prevention

How can similar issues be avoided?

Examples

Better validation

Additional Playwright test

Improved typing

Repository abstraction

Architecture update

Coding standard update

---

# Lessons Learned

Record engineering insights gained from this issue.

Consider whether:

- An ADR should be created.
- A coding standard should change.
- Additional monitoring is needed.
- A reusable utility should be introduced.

---

# Verification

Verified By

Verification Date

Environment

Result

---

# Release Notes

Describe whether this fix should appear in release notes.

If yes, provide a concise user-facing summary.

---

# Guiding Principle

Fix the root cause rather than the symptom.

Every bug should make the platform more reliable, improve engineering knowledge and reduce the likelihood of similar issues in the future.