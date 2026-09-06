# Architecture

## Status

Draft — MVP architecture.

## Purpose

Define the high-level architecture of the Ammu Assignment Review System.

The system is designed to help a Grade 9 student independently improve school assignments using AI as a rigorous reviewer rather than as an assignment writer.

---

## Core Architectural Principle

> The student owns the work. The system owns the challenge.

The system should help the student:

- understand the assignment
- understand the marking criteria
- plan their approach
- identify weaknesses
- test their reasoning
- improve analysis
- validate evidence and claims
- check against the rubric
- improve grammar and expression
- perform a final "tough teacher" review

The system must not become an automated assignment-writing service.

---

## High-Level Flow

Assignment Brief
        |
        v
Task Analysis
        |
        v
Rubric Analysis
        |
        v
Success Criteria
        |
        v
Student Planning
        |
        v
Student Draft
        |
        v
Focused Review
        |
        +--> Evidence Review
        +--> Analysis Review
        +--> Accuracy Review
        +--> Structure Review
        +--> Grammar Review
        |
        v
Rubric Mapping
        |
        v
Priority Improvements
        |
        v
Student Revision
        |
        v
Final Teacher Attack
        |
        v
Final Review

---

## Architectural Components

### 1. Assignment Workspace

Responsible for storing and presenting:

- assignment question
- task instructions
- marking criteria
- teacher requirements
- word count
- due date
- student's notes
- student's research
- student's drafts
- review history

---

### 2. Assignment Understanding Engine

Analyses the assignment brief and identifies:

- explicit requirements
- implicit requirements
- required evidence
- expected response type
- assessment terminology
- likely high-value areas
- potential traps

Output:

`AssignmentSuccessCriteria`

---

### 3. Rubric Analyzer

Converts the teacher's marking criteria into structured requirements.

For example:

- criterion
- performance levels
- outstanding-level requirements
- evidence expected
- analysis expected
- justification expected

The rubric remains the source of truth for assessment.

The system must not invent criteria that are not supported by the supplied rubric.

---

### 4. Review Engine

The review engine contains focused reviewers rather than one general-purpose reviewer.

Initial reviewers:

- Evidence Reviewer
- Analysis Reviewer
- Accuracy Reviewer
- Structure Reviewer
- Grammar/Expression Reviewer
- Rubric Reviewer

Each reviewer should have a narrow responsibility.

---

### 5. Review Orchestrator

LangGraph is the intended orchestration mechanism for multi-step review workflows.

The graph should coordinate deterministic review stages and preserve review state.

The initial implementation should avoid unnecessary autonomous-agent behaviour.

Prefer predictable nodes with explicit inputs and outputs.

---

### 6. Priority Engine

The system should not overwhelm the student with every possible improvement.

It should identify:

1. Critical issues
2. Highest-impact improvements
3. Secondary improvements
4. Optional polishing

The system must always be capable of producing:

> "If you only fix one thing, fix this."

---

### 7. Student Revision Loop

The student remains responsible for making changes.

The system should provide:

- observations
- questions
- challenges
- hints
- examples of what is missing

It should not automatically replace the student's writing.

---

### 8. Final Teacher Attack

The final review deliberately adopts a strict-marker perspective.

Question:

> "If I wanted to give this student one mark less than full marks, what evidence would justify that decision?"

The output should identify the remaining gaps against the supplied rubric.

---

## Subject-Agnostic Core

The system should support multiple school subjects.

The core workflow remains:

Task
→ Rubric
→ Evidence
→ Reasoning
→ Analysis
→ Conclusion
→ Rubric alignment

Subject-specific review rules should be added separately.

---

## Subject Analysis Patterns

### English

WHAT → HOW → WHY → SO WHAT?

### History

WHAT → EVIDENCE → WHY → HISTORICAL SIGNIFICANCE

### Legal Studies / Commerce

WHAT → LAW/EVIDENCE → EFFECT → SIGNIFICANCE TO SOCIETY

### Science

CLAIM → EVIDENCE → EXPLANATION → SIGNIFICANCE

These are review frameworks, not templates for students to mechanically follow.

---

## Technology Direction

Initial application stack:

- TypeScript
- React-based UI
- shadcn/ui
- Vercel deployment
- automated testing with Vitest and Playwright

AI orchestration:

- LangGraph
- LLM provider abstraction to avoid hard-coupling the product to one model

Exact AI provider and production persistence architecture remain implementation decisions.

---

## Architectural Principles

1. Student work is the source material.
2. Teacher rubric is the assessment source of truth.
3. AI feedback should be explainable.
4. Reviewers should have narrow responsibilities.
5. Student remains responsible for revisions.
6. Preserve student voice.
7. Avoid unnecessary autonomous-agent behaviour.
8. Prefer structured outputs over free-form reviewer responses.
9. Every review should be traceable to evidence in the student's work or rubric.
10. Do not manufacture facts, evidence, citations or requirements.