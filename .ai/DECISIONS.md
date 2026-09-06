# Decisions

## Decision Log

This document records significant product and architectural decisions.

---

## ADR-001 — AI is a reviewer, not an author

### Decision

The system will prioritise reviewing, questioning and challenging student work rather than generating assignment content.

### Rationale

The primary educational objective is to improve the student's independent thinking and writing ability.

### Consequence

The system should favour:

- questions
- observations
- challenges
- hints
- targeted suggestions

over complete rewrites.

---

## ADR-002 — Teacher rubric is the source of truth

### Decision

When a marking rubric is provided, the rubric takes precedence over generic assumptions about what constitutes a good assignment.

### Rationale

Different teachers and subjects assess different skills.

### Consequence

The system must distinguish:

- rubric-supported requirements
- general academic advice
- AI inference

---

## ADR-003 — Review before proofreading

### Decision

Content and reasoning are reviewed before grammar and expression.

### Rationale

Grammar improvements have limited value when the underlying argument is weak.

---

## ADR-004 — Prioritise high-impact feedback

### Decision

The system should identify the highest-impact improvements rather than presenting a long undifferentiated list.

### Rationale

Students can become overwhelmed by large numbers of AI suggestions.

---

## ADR-005 — Preserve student ownership

### Decision

The student must remain responsible for implementing changes.

### Rationale

The system exists to develop independent academic capability.

---

## ADR-006 — Structured reviewer outputs

### Decision

AI reviewers should return structured data wherever practical.

### Rationale

Structured outputs allow multiple reviewers to be combined consistently and make the UI easier to build and test.

---

## ADR-007 — LangGraph for orchestration

### Decision

LangGraph will be used for multi-step AI review orchestration.

### Rationale

The workflow contains multiple stages, reviewer nodes and revision loops.

### Constraint

Do not introduce autonomous multi-agent behaviour unless it provides clear value.

---

## ADR-008 — Subject-agnostic core

### Decision

The core review system should support multiple subjects.

### Rationale

The underlying workflow of task understanding, rubric mapping, evidence evaluation and review is reusable.

Subject-specific logic will be layered on top.