# CODING_STANDARDS.md

# Assignment Review System

Coding Standards

Version: 1.0

Owner: Cerosh Jacob

---

# Purpose

This document defines the coding standards for the project.

The goal is to ensure the codebase remains:

- Consistent
- Readable
- Maintainable
- Testable
- Scalable
- AI-friendly

These standards apply to every contributor, including AI assistants.

---

# Core Engineering Principles

Always optimise for:

- Readability
- Simplicity
- Maintainability
- Explicitness
- Predictability

Code is read far more often than it is written.

Optimise for the next engineer.

---

# General Rules

Write code that is:

Simple.

Predictable.

Well structured.

Strongly typed.

Self-documenting.

Avoid clever solutions.

Avoid unnecessary abstractions.

---

# Naming Conventions

Names should describe intent.

Avoid abbreviations.

Good

SubmissionCard

PageHeader

SubmissionRepository

SearchFilters

CategoryList

Bad

Card2

DataUtil

Manager

Helper

Temp

Test1

---

Variables

Prefer descriptive names.

Good

submission

categories

featuredSubmissions

searchResults

Bad

obj

arr

temp

data

item

value

---

Functions

Functions should describe behaviour.

Examples

getSubmissionBySlug()

filterSubmissions()

sortSubmissions()

formatPhoneNumber()

Avoid

handleStuff()

process()

execute()

run()

---

Boolean Variables

Always start with:

is

has

can

should

Examples

isFeatured

hasReviews

canEdit

shouldDisplay

---

File Naming

React Components

PascalCase

SubmissionCard.tsx

PageHero.tsx

Repository Files

camelCase

submissionRepository.ts

Utility Files

camelCase

formatDate.ts

Hooks

useSearch.ts

useScrollPosition.ts

JSON Files

kebab-case

submissions.json

categories.json

---

Folder Naming

Lowercase.

Use hyphens only when required.

Example

components/

features/

repositories/

services/

---

React Standards

Prefer:

Server Components

Use Client Components only when necessary.

Avoid unnecessary client rendering.

---

Component Rules

A component should have one responsibility.

A component should be understandable within a few minutes.

If a component exceeds approximately 200 lines, consider splitting it.

Avoid deeply nested JSX.

Extract repeated UI.

---

Component Structure

Recommended order

Imports

Types

Constants

Hooks

Derived values

Handlers

Render

Export

Maintain consistency.

---

Props

Always type props.

Avoid

any

Prefer explicit interfaces.

Example

interface SubmissionCardProps

Avoid anonymous inline types when reused.

---

State Management

Prefer:

Derived state

Local state

React Context

Avoid global state until justified.

Never duplicate state.

---

Effects

Avoid unnecessary useEffect.

Most effects indicate an architectural smell.

Prefer:

Server Components

Derived values

Memoisation when justified.

---

TypeScript Standards

Strict mode enabled.

Never disable TypeScript checks.

Never ignore compiler errors.

---

Avoid

any

Prefer

unknown

Generics

Union Types

Discriminated Unions

Readonly types where appropriate.

---

Interfaces vs Types

Prefer:

type

for unions and aliases.

Prefer:

interface

for object contracts intended to be extended.

Maintain consistency.

---

Null Handling

Prefer explicit null handling.

Avoid:

!

(non-null assertion)

Use optional chaining.

Use nullish coalescing.

Handle undefined safely.

---

Imports

Group imports.

Order

React

Third-party

Internal

Relative

Separate groups with a blank line.

Avoid deep relative paths.

Prefer aliases.

Example

@/components

@/features

@/lib

---

Functions

Functions should do one thing.

Prefer pure functions.

Avoid hidden side effects.

Small functions are easier to understand.

---

Magic Numbers

Avoid.

Use named constants.

Bad

if (items.length > 7)

Good

const MAX_FEATURED_ITEMS = 7

---

Comments

Avoid comments explaining obvious code.

Good comments explain:

Why.

Not:

What.

Example

Good

// Ranking intentionally prioritises the most recently graded submissions.

Bad

// Increment i.

---

Error Handling

Never silently ignore errors.

Provide meaningful messages.

Log useful information.

Fail gracefully.

---

Async Code

Prefer

async/await

Avoid deeply nested Promise chains.

Handle failures explicitly.

---

CSS

Use Tailwind.

Avoid inline styles.

Avoid custom CSS unless necessary.

Create reusable components before repeating utility classes.

---

Responsive Design

Mobile First.

Test every page on:

Mobile

Tablet

Desktop

Large Desktop

---

Accessibility

Use semantic HTML.

Every input requires a label.

Buttons must be keyboard accessible.

Images require alt text.

Never use colour alone to communicate information.

---

Performance

Measure before optimising.

Prefer:

Server Components

Lazy Loading

Image Optimisation

Code Splitting

Avoid premature optimisation.

---

Repository Pattern

UI must never directly read JSON.

Always access data through repositories.

Example

SubmissionRepository

↓

JSONRepository

↓

JSON

Future

SubmissionRepository

↓

SupabaseRepository

↓

Database

UI remains unchanged.

---

Scripts

CLI entrypoints live directly in `scripts/`, kebab-case, run via `tsx`.

Example

scripts/validate-doc-freshness.ts

scripts/validate-sprint-consistency.ts

Shared helpers used by more than one script live in `scripts/lib/`, camelCase — never duplicated
per-script.

Example

scripts/lib/docChecks.ts

scripts/lib/gitDiff.ts

Every entrypoint starts with `#!/usr/bin/env tsx`. Any entrypoint with a co-located test (below)
guards its `main()` call with `isMainModule(import.meta.url)` (`scripts/lib/isMainModule.ts`), so
importing the module from its own test never executes it as a side effect.

Register every entrypoint as an npm script (`package.json`) rather than invoking `tsx` directly, so
usage stays discoverable via `npm run`.

Co-locate each script's test as `<script-name>.test.ts` next to it, not in a separate `__tests__`
folder.

---

Testing Philosophy

Write code that is easy to test.

Avoid tightly coupled logic.

Prefer dependency injection where appropriate.

Business logic should not depend on UI.

---

Git Standards

Branch Names

feature/

bugfix/

hotfix/

release/

experiment/

Commit Messages

Use Conventional Commits.

Examples

feat:

fix:

docs:

style:

refactor:

perf:

test:

build:

chore:

---

Pull Requests

A PR should solve one problem.

Avoid mixing unrelated changes.

Every PR should include:

Purpose

Approach

Testing

Screenshots (if UI)

Known limitations

---

Code Review Checklist

Review for:

✓ Readability

✓ Maintainability

✓ Type safety

✓ Accessibility

✓ Responsive behaviour

✓ Performance

✓ Reusability

✓ Error handling

✓ Simplicity

✓ Security

---

AI Development Rules

When generating code:

Reuse existing components.

Reuse existing utilities.

Avoid duplication.

Follow existing naming.

Respect folder structure.

Never introduce a new pattern without justification.

Explain trade-offs.

Do not over-engineer.

---

Definition of Clean Code

Good code is:

Easy to understand.

Easy to modify.

Easy to test.

Easy to review.

Easy to delete.

If a new engineer can understand a feature in less than ten minutes, the implementation is probably simple enough.

---

Definition of Done

Code is complete only when:

✓ Builds successfully

✓ Passes linting

✓ Passes type checking

✓ Follows architecture

✓ Follows naming conventions

✓ Is accessible

✓ Is responsive

✓ Is reusable

✓ Has no unnecessary complexity

✓ Is ready for production