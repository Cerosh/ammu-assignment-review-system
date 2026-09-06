# PROMPT_PLAYBOOK.md

# AI Engineering Prompt Playbook

Version: 1.0

Owner: Cerosh Jacob

Purpose:
Reusable prompts for Claude Code.

These prompts standardise the way AI contributes to the project.

---

# General Rule

Before every prompt, Claude should read:

- CLAUDE.md
- PROJECT.md
- ARCHITECTURE.md
- CODING_STANDARDS.md
- CONTEXT.md
- TODO.md

If there is any conflict, the more specific document takes precedence.

---

# 1. Start Development Session

## Purpose

Begin work on the current sprint.

### Prompt

Read:

- CLAUDE.md
- PROJECT.md
- ARCHITECTURE.md
- CONTEXT.md
- TODO.md

Summarise:

- Current sprint objective
- Current project status
- Files likely to be affected
- Risks
- Assumptions

Then explain your implementation approach.

Only after approval should implementation begin.

---

# 2. Build Current Sprint

## Purpose

Implement the current sprint.

### Prompt

Read the current sprint from TODO.md.

Implement only the requested work.

Do not implement future roadmap items.

Reuse existing components.

Follow all coding standards.

After implementation:

- Explain architectural decisions.
- Suggest improvements.
- Recommend a Conventional Commit message.

Stop when the sprint is complete.

---

# 3. Build New Feature

## Purpose

Create a production-ready feature.

### Prompt

Before coding:

Explain:

- affected components
- dependencies
- architectural impact
- reusable opportunities

Then implement the feature.

Requirements:

- Strong typing
- Responsive
- Accessible
- Production quality

Avoid unnecessary abstraction.

---

# 4. Refactor

## Purpose

Improve existing code.

### Prompt

Refactor without changing behaviour.

Improve:

- readability
- maintainability
- consistency

Reduce duplication.

Simplify where possible.

Do not introduce breaking changes.

Explain all major refactoring decisions.

---

# 5. Fix TypeScript

## Purpose

Resolve compiler issues.

### Prompt

Fix all TypeScript errors.

Do not suppress errors.

Do not use "any".

Prefer proper typing.

Explain why each change was necessary.

---

# 6. Fix ESLint

## Purpose

Resolve linting issues.

### Prompt

Fix all ESLint warnings and errors.

Maintain behaviour.

Follow project coding standards.

Avoid disabling lint rules.

---

# 7. Code Review

## Purpose

Review as a Principal Engineer.

### Prompt

Review this implementation.

Check:

- architecture
- naming
- readability
- duplication
- accessibility
- security
- performance
- responsiveness
- TypeScript
- maintainability

Do not rewrite code.

Provide findings grouped by severity:

Critical

High

Medium

Low

Positive observations

---

# 8. Security Review

## Purpose

Perform a security audit.

### Prompt

Review this code using OWASP principles.

Identify:

- XSS
- injection
- validation
- authentication risks
- authorisation issues
- exposed secrets
- insecure dependencies

Suggest improvements.

---

# 9. Accessibility Review

## Purpose

Audit accessibility.

### Prompt

Review this page against WCAG AA.

Evaluate:

- semantic HTML
- keyboard navigation
- focus management
- ARIA usage
- colour contrast
- screen reader compatibility
- reduced motion

List improvements.

---

# 10. Performance Review

## Purpose

Optimise performance.

### Prompt

Review this implementation.

Identify:

- unnecessary renders
- large bundles
- unnecessary client components
- expensive computations
- image optimisation opportunities
- lazy loading opportunities

Recommend improvements.

---

# 11. Responsive Review

## Purpose

Validate responsive behaviour.

### Prompt

Review the UI for:

- mobile
- tablet
- desktop
- large desktop

Identify layout issues.

Suggest improvements.

---

# 12. Design Review

## Purpose

Validate UI consistency.

### Prompt

Review this implementation against DESIGN_SYSTEM.md.

Evaluate:

- spacing
- typography
- colours
- visual hierarchy
- alignment
- consistency
- usability

Suggest improvements.

---

# 13. Generate Placeholder Data

## Purpose

Create demo content.

### Prompt

Generate realistic placeholder data.

Requirements:

- realistic, believable records
- varied categories/statuses
- consistent formatting

Return valid JSON only.

---

# 14. Generate Sample Images

## Purpose

Prepare image placeholders.

### Prompt

List placeholder image requirements.

Do not generate images.

Provide filenames, dimensions and descriptions.

---

# 15. Architecture Review

## Purpose

Review system architecture.

### Prompt

Review the project architecture.

Identify:

- unnecessary coupling
- missing abstractions
- premature abstractions
- scalability concerns
- maintainability concerns

Provide recommendations.

---

# 16. Documentation Review

## Purpose

Ensure documentation remains accurate.

### Prompt

Compare the implementation against:

PROJECT.md

ARCHITECTURE.md

ROADMAP.md

TODO.md

Identify outdated documentation.

Recommend updates.

---

# 17. Git Review

## Purpose

Prepare changes for commit.

### Prompt

Summarise:

- files changed
- purpose
- architectural impact

Recommend:

- commit message
- branch name
- pull request title

---

# 18. Production Readiness Review

## Purpose

Evaluate release quality.

### Prompt

Review the application as if preparing for production.

Evaluate:

- performance
- accessibility
- SEO
- security
- responsiveness
- maintainability
- documentation

List blockers.

Recommend release readiness.

---

# 19. End Sprint

## Purpose

Close the sprint.

### Prompt

Summarise:

- completed work
- architectural decisions
- technical debt
- risks
- documentation updates

Recommend:

- next sprint
- TODO.md updates
- ROADMAP.md updates

Stop after completing the summary.

---

# 20. Explain Before Coding

## Purpose

Avoid blind code generation.

### Prompt

Before writing any code:

Explain:

- your understanding
- proposed solution
- alternatives considered
- trade-offs
- risks

Wait for confirmation before implementation.

---

# Prompting Principles

Every prompt should encourage Claude to:

Understand first.

Explain before coding.

Prefer existing patterns.

Avoid unnecessary abstractions.

Produce production-quality code.

Think like a senior engineer.

Challenge poor assumptions respectfully.

Optimise for maintainability.

Never optimise prematurely.

---

# Golden Rule

The objective is not to generate code quickly.

The objective is to build software that remains easy to understand, maintain and evolve years into the future.

Every prompt should reinforce that philosophy.