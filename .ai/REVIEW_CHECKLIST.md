# REVIEW_CHECKLIST.md

# Engineering Review Checklist

Version: 1.0

Owner: Cerosh Jacob

Purpose:
Provide a consistent review framework for every change made to the project.

This checklist applies to all contributors, including AI-generated code.

---

# Review Philosophy

The objective of a review is to improve the software, not criticise the developer.

A good review should:

- Protect the architecture
- Improve readability
- Reduce maintenance cost
- Improve user experience
- Reduce technical debt
- Encourage consistency

Reviews should explain *why* something should change, not simply state that it is wrong.

---

# Review Process

Review changes in the following order:

1. Requirements
2. Architecture
3. User Experience
4. Code Quality
5. Performance
6. Accessibility
7. Security
8. Testing
9. Documentation

---

# 1. Requirements Review

Verify:

- [ ] The implementation satisfies the requirements in TODO.md.
- [ ] No unnecessary functionality has been added.
- [ ] No requested functionality is missing.
- [ ] Acceptance criteria are met.
- [ ] The solution aligns with PROJECT.md.
- [ ] The implementation respects ROADMAP.md.

Questions

- Does this solve the actual problem?
- Is the implementation appropriately sized?
- Has scope creep been avoided?

---

# 2. Architecture Review

Verify:

- [ ] ARCHITECTURE.md has been followed.
- [ ] Layers remain separated.
- [ ] Repository pattern is respected.
- [ ] UI does not access data sources directly.
- [ ] Components have a single responsibility.
- [ ] Business logic remains inside Features.
- [ ] Components are reusable.
- [ ] Dependencies are justified.

Questions

- Does this simplify the architecture?
- Does it introduce unnecessary coupling?
- Will this scale?

---

# 3. Design Review

Verify:

- [ ] DESIGN_SYSTEM.md has been followed.
- [ ] Consistent spacing.
- [ ] Consistent typography.
- [ ] Appropriate colour usage.
- [ ] Responsive layout.
- [ ] Visual hierarchy is clear.
- [ ] Components match existing patterns.

Questions

- Does this feel like the rest of the application?
- Would a user immediately understand this page?

---

# 4. Component Review

Verify:

- [ ] Components have a single responsibility.
- [ ] Props are well typed.
- [ ] Components are reusable.
- [ ] JSX remains readable.
- [ ] Logic is appropriately extracted.
- [ ] Duplication has been avoided.

Questions

- Can this component be understood in a few minutes?
- Can it be reused elsewhere?

---

# 5. TypeScript Review

Verify:

- [ ] Strict typing is maintained.
- [ ] No `any` types have been introduced.
- [ ] Types are reusable where appropriate.
- [ ] Interfaces and types are well organised.
- [ ] Null handling is explicit.
- [ ] Compiler warnings are resolved.

Questions

- Will future refactoring remain safe?

---

# 6. Readability Review

Verify:

- [ ] Names clearly describe intent.
- [ ] Functions are concise.
- [ ] Magic numbers have been removed.
- [ ] Complex logic has been simplified.
- [ ] Comments explain *why*, not *what*.
- [ ] Code is self-documenting.

Questions

- Could a new engineer understand this quickly?
- Would I enjoy maintaining this six months from now?

---

# 7. Performance Review

Verify:

- [ ] Server Components are used where appropriate.
- [ ] Client Components are justified.
- [ ] Images are optimised.
- [ ] Expensive work is minimised.
- [ ] Bundle size has not unnecessarily increased.
- [ ] Lazy loading is used where beneficial.

Questions

- Is this the simplest performant solution?
- Has optimisation remained evidence-based?

---

# 8. Accessibility Review

Verify:

- [ ] Semantic HTML.
- [ ] Keyboard navigation.
- [ ] Visible focus states.
- [ ] Colour contrast.
- [ ] Accessible labels.
- [ ] Images include alt text.
- [ ] Screen reader compatibility.
- [ ] Reduced motion considerations.

Target

WCAG AA.

Questions

- Can this page be used without a mouse?

---

# 9. Responsive Review

Verify:

- [ ] Mobile.
- [ ] Tablet.
- [ ] Desktop.
- [ ] Large Desktop.
- [ ] No horizontal scrolling.
- [ ] Touch targets are appropriately sized.

Questions

- Would this work comfortably on a phone?

---

# 10. Security Review

Verify:

- [ ] Input validation.
- [ ] Output encoding.
- [ ] No secrets in source code.
- [ ] Safe handling of external data.
- [ ] Dependency risks considered.
- [ ] No obvious OWASP vulnerabilities.

Questions

- What happens if an attacker controls the input?

---

# 11. Data Review

Verify:

- [ ] Repository pattern respected.
- [ ] JSON access isolated.
- [ ] Data validation present where required.
- [ ] Future database migration remains straightforward.

Questions

- Would replacing JSON with Supabase require UI changes?

---

# 12. Testing Review

Verify:

- [ ] Existing functionality has not regressed.
- [ ] Logic is testable.
- [ ] Components are deterministic.
- [ ] Edge cases considered.
- [ ] Error paths handled.

Future

- Unit Tests
- Playwright E2E Tests
- Accessibility Tests

Questions

- What would happen if this failed?

---

# 13. Documentation Review

Verify:

- [ ] README updated if required.
- [ ] CONTEXT.md updated if project status changed.
- [ ] DECISIONS.md updated for major architectural choices.
- [ ] ROADMAP.md updated if priorities changed.
- [ ] TODO.md updated after sprint completion.

Questions

- Would another engineer know what changed?

---

# 14. Git Review

Verify:

- [ ] Commit messages follow Conventional Commits.
- [ ] Branch naming follows project standards.
- [ ] Changes are logically grouped.
- [ ] No unrelated changes included.

Questions

- Would this commit be easy to revert?

---

# AI Review

Before accepting AI-generated code, verify:

- [ ] Existing patterns were reused.
- [ ] No unnecessary abstractions were introduced.
- [ ] The architecture was respected.
- [ ] Trade-offs were explained.
- [ ] Generated code is understood by the reviewer.
- [ ] No code was accepted purely because "AI suggested it."

AI should accelerate engineering, not replace engineering judgement.

---

# Release Checklist

Before merging into the main branch:

- [ ] Build succeeds.
- [ ] Lint succeeds.
- [ ] Type checking succeeds.
- [ ] Responsive verification completed.
- [ ] Accessibility review completed.
- [ ] Documentation updated.
- [ ] No critical review findings remain.
- [ ] Definition of Done satisfied.

---

# Review Severity

## Critical

Must be fixed before merge.

Examples:

- Security vulnerability.
- Data corruption risk.
- Broken functionality.
- Build failure.
- Accessibility blocker.

---

## High

Should be fixed before merge.

Examples:

- Architecture violation.
- Significant performance issue.
- Maintainability concern.
- Incorrect behaviour.

---

## Medium

Should be addressed soon.

Examples:

- Minor duplication.
- Naming inconsistency.
- Refactoring opportunity.
- Documentation improvement.

---

## Low

Optional improvement.

Examples:

- Formatting.
- Minor readability enhancement.
- Small UI polish.

---

# Definition of an Excellent Review

An excellent review:

- Improves the product.
- Improves the architecture.
- Improves the maintainability.
- Teaches something useful.
- Explains reasoning.
- Respects the contributor.

The goal is not to find the most issues.

The goal is to help the team consistently build software that is easier to understand, easier to maintain and more valuable to its users.