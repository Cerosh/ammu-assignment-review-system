# JSON Schema

## Purpose

Define the canonical data structures used by the Ammu Assignment Review System.

The schemas provide predictable contracts between the application and AI review nodes.

---

## Assignment

```json
{
  "id": "string",
  "title": "string",
  "subject": "string",
  "yearLevel": 9,
  "taskQuestion": "string",
  "instructions": "string",
  "wordLimit": "number|null",
  "dueDate": "string|null"
}
```

---

## RubricCriterion

```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "performanceLevels": [
    {
      "level": "string",
      "marks": "number|null",
      "descriptor": "string"
    }
  ],
  "topBandRequirements": [
    "string"
  ]
}
```

---

## SuccessCriteria

```json
{
  "requirements": [
    {
      "id": "string",
      "description": "string",
      "source": "rubric|task|instruction|inference",
      "importance": "critical|high|medium|low"
    }
  ],
  "reviewQuestions": [
    "string"
  ]
}
```

---

## EvidenceReview

```json
{
  "claim": "string",
  "evidence": "string",
  "relationship": "strong|partial|weak|unsupported",
  "explanation": "string",
  "suggestedThinking": "string"
}
```

---

## AnalysisReview

```json
{
  "what": {
    "status": "strong|partial|missing",
    "observation": "string"
  },
  "how": {
    "status": "strong|partial|missing",
    "observation": "string"
  },
  "why": {
    "status": "strong|partial|missing",
    "observation": "string"
  },
  "soWhat": {
    "status": "strong|partial|missing",
    "observation": "string"
  }
}
```

---

## ReviewIssue

```json
{
  "id": "string",
  "category": "content|evidence|analysis|accuracy|structure|grammar|rubric",
  "severity": "critical|high|medium|low",
  "location": "string",
  "observation": "string",
  "whyItMatters": "string",
  "studentQuestion": "string"
}
```

---

## RubricAssessment

```json
{
  "criterionId": "string",
  "currentLevel": "limited|basic|sound|high|outstanding",
  "confidence": "low|medium|high",
  "evidence": [
    "string"
  ],
  "gapToNextLevel": [
    "string"
  ]
}
```

---

## PriorityImprovement

```json
{
  "issueId": "string",
  "priority": 1,
  "title": "string",
  "reason": "string",
  "studentAction": "string"
}
```

---

## FinalReview

```json
{
  "overallAssessment": "string",
  "rubricAssessment": [],
  "strengths": [],
  "criticalIssues": [],
  "priorityImprovements": [],
  "finalTeacherAttack": {
    "whyNotFullMarks": [],
    "lastThingsToCheck": []
  }
}
```

---

## Implementation Notes

These structures define the intended logical contracts between the application and AI review workflow.

They are not implementation-specific.

The implementation may use TypeScript types, Zod schemas, LangGraph state, or other runtime validation mechanisms.

Implementation schemas must remain aligned with these contracts.
