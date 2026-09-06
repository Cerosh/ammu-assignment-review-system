# Design System

## Design Goal

The interface should feel like a calm, supportive academic coaching environment.

It should not feel like:

- a chatbot playground
- an AI content generator
- a grading machine
- a corporate productivity application

---

## Design Principles

### 1. Student-first

The student's work should remain the primary content.

### 2. Clarity over decoration

The interface should make feedback easy to understand and act upon.

### 3. Encourage thinking

Questions and challenges should be visually distinct from instructions.

### 4. Avoid anxiety

The system can be rigorous without making the student feel judged.

### 5. Show progress

The student should be able to see how their work improves across review cycles.

---

## Visual Language

Use the existing shadcn/ui foundation.

Prefer:

- clean cards
- clear headings
- restrained badges
- simple status indicators
- readable typography
- generous spacing
- responsive layouts

Avoid unnecessary animation.

---

## Review Status

Use consistent semantic states:

- 🟢 Strong
- 🟡 Developing
- 🟠 Needs attention
- 🔴 Critical

These should not be interpreted as actual school marks unless explicitly mapped to the rubric.

---

## Key UI Components

Initial components may include:

- AssignmentCard
- RubricCard
- SuccessCriteria
- DraftEditor
- ReviewPanel
- ReviewerCard
- EvidenceCheck
- RubricMapping
- PriorityIssue
- RevisionChecklist
- FinalTeacherAttack
- AssignmentTimeline

---

## Feedback Hierarchy

Every review should visually distinguish:

### What you're doing well

Positive evidence.

### What needs attention

Specific weakness.

### Why it matters

Connection to rubric or task.

### Think about this

Question for the student.

### Priority

The most important action.

---

## Student Language

Use language appropriate for a Grade 9 student.

Prefer:

> "Your evidence is good, but I don't yet see why it matters."

over:

> "Your evidentiary substantiation lacks sufficient analytical depth."

---

## Accessibility

The application should:

- support keyboard navigation
- maintain sufficient contrast
- use semantic HTML
- provide visible focus states
- avoid relying only on colour
- support responsive layouts

Use the existing accessibility and UI standards in the generic project documentation.