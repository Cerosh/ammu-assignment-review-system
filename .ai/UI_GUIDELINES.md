# UI_GUIDELINES.md

# User Interface Guidelines

Assignment Review System

Version: 1.0

Owner: Cerosh Jacob

Last Updated: 2026-07-06

---

# Purpose

This document defines the user interface principles for the project.

It ensures every screen feels consistent, intuitive and trustworthy.

The goal is not simply to create attractive interfaces, but to create interfaces that help users accomplish tasks with minimal effort.

---

# UI Philosophy

The best interface is one that feels obvious.

Users should never have to think about how to use the application.

Design should reduce cognitive load.

Every screen should answer:

- Where am I?
- What can I do?
- What should I do next?

---

# Core Principles

Every interface should be:

Simple

Clear

Fast

Accessible

Consistent

Responsive

Predictable

Trustworthy

---

# Visual Hierarchy

Guide the user's attention intentionally.

Prioritise:

1. Primary action
2. Main content
3. Supporting information
4. Secondary actions
5. Metadata

Avoid presenting everything with equal emphasis.

---

# Layout Principles

Use generous whitespace.

Avoid clutter.

Group related information.

Maintain consistent alignment.

Respect the spacing scale defined in DESIGN_SYSTEM.md.

Every page should have:

- Clear page title
- Supporting description where helpful
- Primary content area
- Consistent footer

---

# Content Width

Maximum content width:

1200px

Reading content:

700–800px

Dashboard-style layouts:

1200–1400px

Avoid excessively wide text columns.

---

# Navigation

Navigation should always answer:

Where am I?

Where can I go?

Primary navigation should remain consistent across the application.

Avoid changing navigation locations between pages.

---

# Mobile-First Design

Design for mobile first.

Enhance progressively for larger screens.

Avoid hiding important functionality on smaller devices.

Ensure touch targets are large enough for comfortable interaction.

---

# Page Structure

Recommended order:

1. Header
2. Hero (if applicable)
3. Search / Filters
4. Main Content
5. Supporting Content
6. Footer

Consistency improves learnability.

---

# Search Experience

Search should be highly visible.

Search should:

- Be available from key pages.
- Respond quickly.
- Handle empty states gracefully.
- Support partial matches.
- Provide helpful messaging when no results are found.

Search is a core feature of the platform.

---

# Forms

Forms should be:

Short

Simple

Well-labelled

Grouped logically

Requirements:

- Labels above inputs
- Helpful placeholder text where appropriate
- Inline validation
- Clear error messages
- Clear success messages

Avoid unnecessary fields.

---

# Buttons

Every screen should have one obvious primary action.

Secondary actions should never compete visually with the primary action.

Use consistent button hierarchy:

Primary

Secondary

Tertiary

Destructive

Avoid multiple competing primary buttons.

---

# Cards

Submission cards should display:

- Submission title
- Category
- Short description
- Status/grade (where appropriate)
- Featured badge (if applicable)

Cards should remain visually consistent across categories.

---

# Lists

Maintain consistent spacing.

Support scanning.

Avoid excessive text.

Provide meaningful empty states.

---

# Tables

Use tables only when comparing structured information.

Avoid tables for mobile-heavy experiences where cards are more appropriate.

---

# Empty States

Every empty state should answer:

Why is nothing displayed?

What should the user do next?

Example

"No submissions found in this category.

Try another category or search for something else."

Avoid blank pages.

---

# Loading States

Avoid sudden layout shifts.

Use skeleton loaders where appropriate.

Keep loading indicators consistent.

---

# Error States

Errors should:

Explain the problem.

Suggest the next step.

Avoid technical language.

Never expose implementation details.

---

# Feedback

Every user action should produce appropriate feedback.

Examples

Loading

Success

Warning

Error

Confirmation

Users should never wonder whether an action succeeded.

---

# Icons

Use icons only when they improve understanding.

Every icon should have meaning.

Avoid decorative icons that add visual noise.

Use a consistent icon library.

---

# Images

Images should:

Support content.

Be optimised.

Have descriptive alt text.

Avoid stock photography where possible.

Future:

Replace placeholders with authentic project imagery.

---

# Colour Usage

Use colour intentionally.

Colour should reinforce meaning.

Never rely on colour alone.

Maintain sufficient contrast.

Follow DESIGN_SYSTEM.md.

---

# Typography

Typography should establish hierarchy.

Use:

Heading

Subheading

Body

Caption

Avoid unnecessary font variations.

---

# Animation

Animation should communicate.

Use subtle transitions.

Avoid distracting effects.

Respect reduced-motion preferences.

Animation should never delay task completion.

---

# Accessibility

Every interface should meet WCAG AA.

Support:

Keyboard navigation.

Screen readers.

Visible focus.

Semantic HTML.

Accessible labels.

Accessibility is a product requirement, not an enhancement.

---

# Responsive Behaviour

Support:

Mobile

Tablet

Desktop

Large Desktop

Avoid horizontal scrolling.

Ensure layouts adapt gracefully.

---

# Consistency

Reuse existing UI patterns.

Avoid creating new interaction models unless necessary.

Consistency reduces learning time.

---

# Submission List Guidelines

Each listing should clearly communicate:

Submission title

Category

Summary

Status/grade

Submitter (if appropriate)

Featured status

Avoid overwhelming users with excessive detail.

---

# Homepage Guidelines

The homepage should immediately communicate:

Who the platform is for.

What users can find.

How to start.

The primary search action should be highly visible.

---

# Trust Signals

Build confidence through:

Consistent branding

Professional design

Accurate information

Clear contact details

User focus

Future:

Verified submitters

Peer recommendations

Claimed profiles

---

# Performance

Users should perceive the application as fast.

Optimise:

Images

Fonts

Animations

JavaScript

Avoid unnecessary delays.

---

# SEO Considerations

Ensure:

Meaningful headings

Semantic HTML

Descriptive page titles

Meta descriptions

Structured data (future)

Readable URLs

---

# AI UI Generation Rules

When generating UI:

Follow existing patterns.

Reuse components.

Respect spacing.

Maintain hierarchy.

Prefer simplicity.

Avoid decorative complexity.

Do not invent new visual patterns without justification.

---

# UI Review Checklist

Before approving a screen:

- [ ] Clear purpose
- [ ] Consistent layout
- [ ] Mobile friendly
- [ ] Accessible
- [ ] Responsive
- [ ] Readable
- [ ] Clear primary action
- [ ] Appropriate feedback
- [ ] Empty states handled
- [ ] Error states handled
- [ ] Uses existing components

---

# Definition of Good UI

A good interface:

Feels familiar.

Requires little explanation.

Supports the user's goal.

Looks consistent.

Performs well.

Builds trust.

Disappears into the background while users accomplish their tasks.

---

# Guiding Principle

Good user interfaces are not remembered because they are visually impressive.

They are remembered because they make the right task feel effortless.

Every design decision should reduce friction, increase clarity and help users achieve their goals.