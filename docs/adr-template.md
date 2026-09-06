# ADR Template

Assignment Review System

This template matches the format actually used by DECISIONS.md's existing ADRs (ADR-001 through ADR-010). Keep new ADRs consistent with it rather than inventing a new structure.

---

# ADR-XXX

## Title

State the decision in a short, specific title.

Example

Use the Repository Pattern for all data access.

Status

Choose one:

- Proposed
- Accepted
- Superseded

Date

YYYY-MM-DD

---

### Context

Describe the background that makes this decision necessary.

Answer: why is this decision needed now?

---

### Decision

State clearly what was decided.

---

### Alternatives Considered

List the realistic alternatives that were weighed.

Example

- Import JSON directly into components.
- Use API routes immediately.
- Repository abstraction.

---

### Rationale

Explain why this option was chosen over the alternatives.

Focus on trade-offs, not on criticising the alternatives.

---

### Consequences

Describe what changes as a result of this decision — both benefits and costs.

---

### Future Review

Describe the condition that should trigger revisiting this decision.

Example

Revisit when supporting more than five communities.

---

# Related ADRs

List any related or superseded Architecture Decision Records.

Example

ADR-002, ADR-003

---

# AI Guidance

When working on code affected by this ADR:

- Follow this decision unless a newer ADR supersedes it.
- Do not introduce alternative patterns without creating a new ADR.
- If implementation conflicts with this ADR, raise the conflict before writing code.

---

# Guiding Principle

Architecture decisions are records of intentional engineering choices.

They exist to explain **why** a decision was made — not merely **what** was implemented.

Good ADRs reduce repeated debates, preserve institutional knowledge and help both engineers and AI assistants make consistent decisions as the project evolves.
