# DEPLOYMENT.md

# Deployment & Release Strategy

Assignment Review System

Version: 1.0

Owner: Cerosh Jacob

Last Updated: 2026-07-06

---

# Purpose

This document defines the deployment strategy for the project.

It describes:

- Environment strategy
- Deployment workflow
- CI/CD expectations
- Release process
- Rollback procedures
- Operational standards

The goal is to make deployments safe, repeatable and predictable.

---

# Deployment Philosophy

Deploy often.

Deploy small.

Deploy safely.

Every deployment should be:

- Reproducible
- Automated
- Observable
- Reversible

Production deployments should never rely on manual changes.

---

# Platform

Current Hosting

Vercel

Current Framework

Next.js 15

Rendering

Server Components

Static Generation where appropriate

Future

Supabase

Cloudflare CDN

Cloudflare Images

Cloudflare R2

---

# Environment Strategy

Development

Purpose

Local development.

Characteristics

- Fast iteration
- Local JSON data
- Debugging enabled

---

Preview

Purpose

Validate Pull Requests.

Characteristics

- Automatic deployment
- Feature validation
- Stakeholder review

Every Pull Request should generate a preview deployment.

---

Production

Purpose

Serve live users.

Characteristics

- Optimised builds
- Monitoring enabled
- Analytics enabled
- Security headers enabled

Only reviewed code should reach production.

---

# Branch Strategy

main

Production-ready code.

develop (optional)

Integration branch for larger initiatives.

feature/*

New functionality.

bugfix/*

Bug fixes.

hotfix/*

Urgent production fixes.

release/*

Release preparation.

---

# Release Workflow

Developer

↓

Feature Branch

↓

Pull Request

↓

Code Review

↓

CI Validation

↓

Preview Deployment

↓

Approval

↓

Merge to Main

↓

Production Deployment

↓

Post Deployment Verification

---

# Continuous Integration

Every Pull Request should execute:

1. Install dependencies

2. Type checking

3. ESLint

4. Unit tests

5. Component tests

6. Playwright smoke tests (when available)

7. Build

8. Deployment preview

A failing CI pipeline blocks merging.

CI also runs the doc-staleness guardrails against the push/PR's commit range — see
`.ai/GIT_WORKFLOW.md`'s "Doc-Staleness Guardrails" section for what each check catches and how to
bypass one with a disclosed `Docs-Deferred:` trailer when genuinely needed.

---

# Continuous Deployment

Current

CI-gated deployment from the `main` branch. Vercel's own Git integration does not auto-deploy
`main` (`vercel.json`'s `git.deploymentEnabled.main` is `false`); the `deploy`
job in `.github/workflows/ci.yml` runs `vercel deploy --prebuilt --prod` only after both the
`checks` and `e2e` jobs pass, using a `VERCEL_TOKEN` secret (plus `VERCEL_ORG_ID`/
`VERCEL_PROJECT_ID`) scoped to this repo. A red build or failing test suite can no longer reach
production. Preview deployments (PRs, non-`main` branches) are unaffected and still deploy
automatically via Vercel's Git integration.

Future

Protected release pipeline with approval gates.

---

# Build Requirements

Every deployment must pass:

- TypeScript
- ESLint
- Build
- No critical vulnerabilities
- Required automated tests
- Documentation updated when necessary

Build failures must be resolved before release.

---

# Environment Variables

Use:

- `.env.local` for local development
- Vercel Environment Variables for hosted environments
- `.env.example` to document required variables

Never commit secrets.

Rotate compromised secrets immediately.

---

# Required Environment Variables

Examples

NEXT_PUBLIC_SITE_URL

SUPABASE_URL (Future)

SUPABASE_ANON_KEY (Future)

SENTRY_DSN (Future)

GOOGLE_ANALYTICS_ID (Future)

Do not add unused variables.

---

# Build Optimisation

Optimise for:

- Small bundles
- Static generation where appropriate
- Image optimisation
- Code splitting
- Tree shaking

Measure before introducing complexity.

---

# Performance Targets

Build Success

100%

Lighthouse

95+

Accessibility

100

Best Practices

100

SEO

95+

Largest Contentful Paint

< 2.5 seconds

Cumulative Layout Shift

< 0.1

---

# Security During Deployment

Verify:

- Security headers enabled
- HTTPS enforced
- Secrets configured
- Debugging disabled in production
- Source maps handled appropriately
- No sensitive data exposed

Follow SECURITY.md.

---

# Observability

Current

Vercel Analytics (planned)

Future

Sentry

Microsoft Clarity

Google Analytics

Error reporting should support investigation without exposing sensitive information.

---

# Logging

Production logs should capture:

- Errors
- Warnings
- Performance metrics
- Request failures

Never log:

- Passwords
- Tokens
- Secrets
- Personal information unless operationally necessary

---

# Release Checklist

Before release:

- [ ] All acceptance criteria met
- [ ] CI passing
- [ ] Build successful
- [ ] No unresolved critical issues
- [ ] Documentation updated
- [ ] Accessibility reviewed
- [ ] Responsive verification completed
- [ ] Performance reviewed
- [ ] Security review completed
- [ ] Product Owner approval (when applicable)

---

# Deployment Checklist

Verify:

- [ ] Environment variables configured
- [ ] Build completed successfully
- [ ] Static assets uploaded
- [ ] Preview deployment verified
- [ ] Production deployment completed
- [ ] Homepage accessible
- [ ] Navigation working
- [ ] Search functioning (when implemented)
- [ ] No console errors
- [ ] Analytics connected (when enabled)

---

# Smoke Tests

Immediately after deployment:

Verify:

- Homepage loads
- Navigation works
- Business directory loads
- Business details open
- Responsive navigation works
- Images load
- Footer renders
- No broken links
- No JavaScript errors

---

# Rollback Strategy

If a deployment introduces a critical issue:

1. Assess impact.
2. Roll back to the previous stable deployment.
3. Investigate root cause.
4. Create a corrective fix.
5. Redeploy after validation.
6. Record significant architectural lessons in DECISIONS.md if appropriate.

Avoid emergency changes directly in production.

---

# Disaster Recovery

Current

Vercel deployment history provides rollback capability.

Future

- Database backups
- Storage backups
- Infrastructure as Code
- Recovery runbooks
- Recovery drills

---

# Future Infrastructure

Version 2

Supabase

Authentication

Database

Storage

Version 3

Cloudflare CDN

Image optimisation

Caching

Version 4

Background jobs

Search indexing

Vector database

Version 5

Multi-region deployments

Advanced monitoring

Scalable infrastructure

---

# Deployment Metrics

Track:

- Deployment frequency
- Lead time for changes
- Build duration
- Change failure rate
- Mean time to recovery (MTTR)
- Availability
- Error rate

Use metrics to guide improvement rather than as performance targets for individuals.

---

# Responsibilities

Developer

- Implement feature
- Run local checks
- Update documentation

Reviewer

- Validate quality
- Approve changes
- Ensure standards are followed

Release Owner

- Confirm readiness
- Monitor deployment
- Coordinate rollback if required

---

# Definition of a Successful Deployment

A deployment is successful when:

- Users experience no unexpected disruption.
- The application behaves as intended.
- Performance remains within targets.
- Monitoring shows no significant regressions.
- Documentation reflects the deployed state.
- The team can confidently continue development.

---

# Guiding Principle

Deployment is not the end of development.

Deployment is the beginning of operating software in the real world.

Every release should leave the platform more stable, more maintainable and more valuable than before.