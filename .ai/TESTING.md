# TESTING.md

# Assignment Review System

Engineering Testing Strategy

Version: 1.0

Owner: Cerosh Jacob

Last Updated: 2026-07-06

---

# Purpose

This document defines the quality strategy for the project.

Testing exists to provide confidence.

It should enable rapid delivery while protecting users from regressions.

Every engineer is responsible for quality.

Testing is not a separate phase.

Testing happens continuously throughout development.

---

# Quality Philosophy

Quality is built into the product.

It is never added afterwards.

Testing should provide confidence rather than simply increase coverage.

We optimise for:

- Reliability
- Maintainability
- Speed
- Confidence
- Fast Feedback

---

# Testing Pyramid

```

                 Manual Exploratory
                      ▲
                 End-to-End Tests
                      ▲
            Integration Tests
                      ▲
               Component Tests
                      ▲
                 Unit Tests

```

The higher the layer, the fewer tests should exist.

The lower the layer, the faster they should execute.

---

# Testing Principles

Every test should be:

Reliable

Deterministic

Independent

Readable

Fast

Maintainable

Tests should document expected behaviour.

---

# Definition of Quality

Software is considered high quality when:

It works.

It is understandable.

It is maintainable.

It is accessible.

It performs well.

It can be confidently changed.

---

# Testing Layers

## Unit Tests

Purpose

Verify core logic.

Examples

Utility functions

Data transformations

Formatting

Validation

Sorting

Filtering

Slug generation

Characteristics

Fast

Independent

No browser

No network

No filesystem

---

## Component Tests

Purpose

Verify isolated UI behaviour.

Examples

Submission Card

Category Card

Search Input

Navigation

Footer

Forms

Verify

Rendering

Props

Interactions

Accessibility

---

## Integration Tests

Purpose

Verify collaboration between components.

Examples

Search + Repository

Filters + Submission List

Homepage + JSON

Submission Details + Recommendations

Verify

Data flow

Integration

Rendering

---

## End-to-End Tests

Purpose

Verify complete user journeys.

Framework

Playwright

Primary Scenarios

Homepage

Search

Browse Submission List

Open Submission

Navigate Categories

Responsive Behaviour

Accessibility

These tests represent user behaviour.

---

## Manual Testing

Used for

Exploratory Testing

Visual Validation

Usability

New Features

Accessibility Review

Cross-device verification

---

# Automation Philosophy

Automate tests that:

Run frequently.

Protect critical behaviour.

Provide long-term value.

Avoid automating unstable functionality.

Automation should reduce maintenance cost.

---

# ROI Philosophy

Every automated test should justify its maintenance cost.

Questions

Will this test run often?

Will failures matter?

Will maintenance remain low?

Will it prevent expensive regressions?

If not, reconsider automation.

---

# Test Coverage Philosophy

Coverage is a metric.

Confidence is the objective.

Avoid chasing 100% coverage.

Prioritise:

Critical paths.

Business value.

User impact.

---

# Critical User Journeys

Homepage loads.

Navigation works.

Search works.

Submission list loads.

Submission page loads.

Responsive navigation.

Contact page.

404 page.

Future

Authentication.

Reviewer Dashboard.

Admin Portal.

Payments.

---

# Playwright Standards

Preferred Structure

```

tests/

fixtures/

pages/

components/

helpers/

data/

```

Use

Page Object Model.

Reusable fixtures.

Deterministic selectors.

Stable assertions.

Avoid brittle selectors.

---

# Playwright Locator Strategy

Preferred order

Role

Label

Placeholder

Text

Test ID

Avoid

XPath

Complex CSS selectors

DOM hierarchy selectors

---

# Test Data

Current

Static JSON

Future

Seeded database

Test data should be:

Predictable

Reusable

Independent

---

# Accessibility Testing

Verify

Keyboard navigation

Screen readers

Focus

ARIA

Semantic HTML

Colour contrast

Reduced motion

Target

WCAG AA

---

# Responsive Testing

Test

Mobile

Tablet

Desktop

Large Desktop

Landscape

Portrait

---

# Browser Support

Primary

Chrome

Secondary

Firefox

Safari

Future

Edge

Mobile Browsers

---

# Performance Testing

Measure

Page Load

LCP

CLS

FID

Bundle Size

Image Loading

Use

Lighthouse

Core Web Vitals

---

# Security Testing

Review

Input validation

Output encoding

Authentication

Authorisation

Secrets

Dependency vulnerabilities

Follow SECURITY.md.

---

# Visual Regression

Future

Playwright Screenshots

Golden Images

Pixel Comparison

Only where valuable.

---

# API Testing

Current

None.

Future

Repository

API

Authentication

Search

Core APIs

---

# AI Feature Testing

Future

Prompt Quality

Fallback Behaviour

Hallucination Handling

Response Time

Error Handling

Guardrails

---

# Test Naming

Names should describe behaviour.

Good

shouldDisplayFeaturedSubmissions()

shouldFilterSubmissionsByCategory()

shouldOpenSubmissionDetails()

Bad

test1()

homepage()

validation()

---

# Definition of Done

Every completed feature should include:

Appropriate testing.

Manual verification.

Accessibility review.

Responsive verification.

Documentation updates.

---

# CI Pipeline

Every Pull Request should execute:

Type Checking

↓

Lint

↓

Unit Tests

↓

Component Tests

↓

Playwright

↓

Build

↓

Deployment Preview

No merge if any stage fails.

---

# Release Checklist

Before release:

✓ Build succeeds

✓ TypeScript passes

✓ Lint passes

✓ Critical Playwright tests pass

✓ Accessibility reviewed

✓ Responsive verified

✓ Performance acceptable

✓ Documentation updated

---

# Bug Classification

Critical

Application unusable.

High

Primary workflow broken.

Medium

Incorrect behaviour.

Low

Cosmetic.

---

# Engineering Metrics

Monitor

Build Success

Deployment Success

Bug Rate

Regression Rate

Playwright Stability

Accessibility Score

Performance Score

Technical Debt

Metrics inform decisions.

They do not replace engineering judgement.

---

# Future Testing Roadmap

Version 2

API Testing

Authentication Testing

Supabase Testing

Version 3

Visual Regression

AI Testing

Performance Monitoring

Version 4

Load Testing

Security Automation

Chaos Testing

Version 5

Multi-tenant Testing

Disaster Recovery Validation

---

# Guiding Principle

The objective is not to prove the software works.

The objective is to make change safe.

Every test should increase confidence.

Every automated test should reduce future maintenance.

Quality is measured by confidence, not by the number of tests.