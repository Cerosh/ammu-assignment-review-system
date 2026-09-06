# Product

## Product Name

Ammu Assignment Review System

## Product Vision

Help students become better at independently producing high-quality school work by giving them access to an AI reviewer that challenges their thinking before their teacher does.

---

## Product Promise

> Your work. Your thinking. AI's toughest review.

---

## Guiding Principles (Decision Framework)

Adopted 2026-09-06, as the north star for every future design decision across
all five stages.

> **North star:** Build an AI that helps Ammu become better at producing
> high-quality assignments herself.

> **Core rule:** Ammu owns the work. The system owns the challenge.

Whenever a design or implementation choice has two paths, prefer the one on
the right:

| Choice | Prefer |
|---|---|
| AI doing the work | AI improving Ammu's thinking |
| Giving her an answer | Asking the right question |
| Fixing one assignment | Building a transferable skill |
| Optimising for marks | Optimising for learning that leads to better marks |

This applies to every stage, not just the review-facing ones -- a prompt's
phrasing, a schema field, a checklist item, or a future UI decision should
all be checked against this table.

---

## Primary User

Ammkuttuy ("Ammu"), Grade 9 student in Sydney.

The system should be designed for her age and academic context but should not be hard-coded exclusively to one student.

---

## Core User Journey

### 1. Start assignment

Student enters or uploads:

- assignment task
- marking criteria
- teacher instructions

### 2. Understand

System explains:

- what the task is asking
- what the top band requires
- what the student needs to demonstrate

### 3. Plan

Student creates their own:

- ideas
- evidence
- structure
- approach

System challenges the plan without writing it.

### 4. Write

Student independently writes the assignment.

### 5. Review

Student submits a draft.

System reviews:

- task alignment
- rubric alignment
- evidence
- analysis
- accuracy
- structure
- grammar

### 6. Revise

Student makes their own changes.

### 7. Final Teacher Attack

System attempts to identify why the work might not receive the top rubric level.

### 8. Submit

Student decides when the work is ready.

---

## Core Features

### MVP

- Create assignment
- Store task and rubric
- Generate success criteria
- Student draft input
- Tough review
- WHAT/HOW/WHY/SO WHAT analysis
- Unsupported-claim detection
- Rubric mapping
- Priority improvement
- Final teacher attack

---

## Future Features

Potential future capabilities:

- paragraph-level review
- research/source review
- subject-specific reviewers
- assignment history
- draft comparison
- recurring weakness detection
- student progress over time
- parent view
- teacher feedback comparison
- voice-based review

These are not part of the initial MVP.

---

## Product Guardrails

The product must not:

- produce a complete submission-ready assignment
- automatically rewrite the student's work
- fabricate sources
- fabricate evidence
- guarantee marks
- encourage academic dishonesty

---

## Success Criteria

The product is successful when the student can independently answer:

- What is my teacher asking?
- What does top-band work require?
- Where is my argument weak?
- What evidence supports my claim?
- What am I missing?
- What should I fix first?
- Why does my evidence matter?

The strongest success signal is not the amount of AI-generated text.

It is the student's ability to improve their own work.