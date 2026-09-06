# Pull Request Template

Assignment Review System

PR Title:

Branch:

Related Feature:

Related Bug:

Related ADR:

Sprint:

Target Release:

---

# Summary

## What does this Pull Request do?

Provide a concise summary of the changes.

Focus on user value and engineering impact rather than implementation details.

---

# Why was this change needed?

Describe the business or technical problem being solved.

Reference:

- Feature document
- Bug report
- ADR
- Roadmap item

---

# Change Type

Select all that apply.

- [ ] New Feature
- [ ] Bug Fix
- [ ] Refactor
- [ ] Performance Improvement
- [ ] Accessibility Improvement
- [ ] Security Improvement
- [ ] Documentation
- [ ] Build / CI
- [ ] Dependency Update
- [ ] UI Enhancement
- [ ] Test Improvement

---

# Scope

## Included

-

-

-

---

## Not Included

-

-

-

Avoid feature creep.

---

# User Impact

Describe what users will notice after this change.

Examples

- Faster search
- Improved navigation
- Better mobile experience
- Fixed business listing issue

---

# Technical Summary

Describe the implementation.

Examples

- Added repository methods
- Created reusable UI component
- Updated JSON schema
- Improved caching
- Refactored feature structure

---

# Files of Interest

List the most important files changed.

Example

```
app/page.tsx

features/search/

repositories/businessRepository.ts

components/BusinessCard.tsx

data/businesses.json
```

---

# Screenshots

For UI changes include:

Desktop

Mobile

Tablet

Before / After (if appropriate)

---

# Testing Performed

Select all completed.

- [ ] Unit Tests
- [ ] Integration Tests
- [ ] Playwright Tests
- [ ] Manual Testing
- [ ] Responsive Testing
- [ ] Accessibility Testing
- [ ] Performance Validation

Describe any additional testing performed.

---

# Test Evidence

Provide evidence where appropriate.

Examples

- Playwright screenshots
- Lighthouse report
- Console output
- Build logs

---

# Accessibility Review

Confirm:

- [ ] Keyboard navigation verified
- [ ] Focus states verified
- [ ] Semantic HTML used
- [ ] ARIA labels reviewed
- [ ] Colour contrast maintained
- [ ] WCAG AA requirements met

---

# Performance Review

Confirm:

- [ ] No unnecessary re-renders
- [ ] Bundle size acceptable
- [ ] Images optimised
- [ ] Lazy loading where appropriate
- [ ] No significant performance regressions

---

# Security Review

Confirm:

- [ ] Input validation reviewed
- [ ] No secrets committed
- [ ] No credentials exposed
- [ ] Security headers unaffected
- [ ] SECURITY.md followed

---

# Documentation

Have the following been updated where necessary?

- [ ] README.md
- [ ] CHANGELOG.md
- [ ] TODO.md
- [ ] CONTEXT.md
- [ ] ROADMAP.md
- [ ] DECISIONS.md
- [ ] ARCHITECTURE.md

If not required, explain why.

---

# Breaking Changes

Does this PR introduce breaking changes?

- [ ] Yes
- [ ] No

If yes, describe:

Migration steps

Backward compatibility

User impact

---

# Deployment Notes

Does deployment require special steps?

Examples

Environment variables

Configuration changes

Database migration

Feature flags

If none:

State:

No special deployment actions required.

---

# Risks

Potential risks introduced.

Examples

Regression

Performance

Accessibility

Browser compatibility

Deployment

Mitigation

Describe how risks have been reduced.

---

# Reviewer Checklist

Please verify:

- [ ] Requirements satisfied
- [ ] Architecture respected
- [ ] Repository pattern followed
- [ ] Components reusable
- [ ] Code readable
- [ ] Type safety maintained
- [ ] No unnecessary complexity
- [ ] Responsive behaviour
- [ ] Accessibility
- [ ] Tests adequate
- [ ] Documentation updated

Reference:

REVIEW_CHECKLIST.md

---

# AI Assistance

Was AI used?

- [ ] Claude Code
- [ ] ChatGPT
- [ ] GitHub Copilot
- [ ] Other
- [ ] No AI assistance

If AI was used:

Confirm:

- [ ] Generated code reviewed
- [ ] Code understood
- [ ] Standards followed
- [ ] Manual verification completed

AI-generated code should never be merged without engineering review.

---

# Rollback Plan

If this PR causes issues:

Describe the rollback approach.

Examples

Revert commit

Disable feature

Restore previous deployment

---

# Release Notes

Provide a short user-facing summary.

Example

Added category filtering to help residents find local businesses more quickly.

---

# Post-Merge Tasks

Complete if required.

- [ ] Delete feature branch
- [ ] Update Sprint document
- [ ] Update CHANGELOG.md
- [ ] Update TODO.md
- [ ] Create follow-up issues
- [ ] Update AI_MEMORY.md (if long-term project knowledge changed)

---

# Final Checklist

Before merging:

- [ ] Build passes
- [ ] CI passes
- [ ] Tests pass
- [ ] Code reviewed
- [ ] Documentation updated
- [ ] No debug code
- [ ] No unnecessary console logs
- [ ] Ready for deployment

---

# Reviewer Comments

Reviewer:

Decision:

- [ ] Approve
- [ ] Request Changes
- [ ] Comment

Notes

---

# Guiding Principle

A Pull Request should tell a complete story.

A reviewer should understand:

- Why the change was made.
- What changed.
- How it was tested.
- What risks exist.
- How it can be safely deployed or reverted.

Every Pull Request should improve the quality, maintainability and reliability of the platform.