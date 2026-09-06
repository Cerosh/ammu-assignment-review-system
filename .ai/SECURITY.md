# SECURITY.md

# Security Standards

Assignment Review System

Version: 1.0

Owner: Cerosh Jacob

Classification: Internal Engineering Standard

Last Updated: 2026-07-06

---

# Purpose

This document defines the security principles, engineering standards and development practices for the project.

Security is everyone's responsibility.

Every feature should be designed with security in mind rather than added afterwards.

---

# Security Philosophy

The platform should be:

- Secure by Default
- Privacy Conscious
- Least Privilege
- Defence in Depth
- Simple to Audit
- Easy to Maintain

Security decisions should reduce long-term risk without unnecessarily increasing complexity.

---

# Security Principles

Always:

Validate input.

Escape output.

Use HTTPS.

Keep dependencies updated.

Protect secrets.

Log security events.

Review third-party libraries.

Never trust client input.

---

# Current MVP Security Scope

Version 1 is a static website.

Included

- Static JSON
- Read-only content
- No authentication
- No payments
- No user accounts
- No backend
- Read-only, server-side integrations with external APIs, via lightweight, stateless Next.js
  Route Handlers — no database, no user accounts, no persistent server state. See "API Security"
  and "Third-Party Services" below for the requirements this adds, once any such integration is
  introduced.

Excluded

- Login
- User-generated content
- Submitter dashboard
- Administration portal
- File uploads
- This project exposing its own API to external consumers (distinct from the read-only external
  API calls now allowed above — see "API Security" below)

The attack surface is intentionally minimal, and every new external API integration is a
deliberate addition to it, reviewed per "Third-Party Services" below — not a blanket exception.

---

# Authentication Strategy

Current

None.

Future

Supabase Authentication.

Supported providers

- Google
- Apple
- Email
- Magic Links

Passwords should never be stored by the application.

---

# Authorisation Strategy

Future implementation should follow Role-Based Access Control (RBAC).

Planned roles

Guest

Resident

Submitter

Moderator

Administrator

Super Administrator

Permissions should be explicit and deny by default.

---

# Secret Management

Never commit:

- API keys
- Access tokens
- Database credentials
- Private certificates
- Encryption keys
- Service account files

Use:

Environment variables.

Platform secret management.

Rotate secrets immediately if exposure is suspected.

---

# Environment Variables

Store secrets in:

.env.local

Never commit `.env*` files unless they are example templates (for example, `.env.example`) with placeholder values.

Provide clear documentation for required variables.

---

# Dependency Management

Before introducing a new dependency:

Verify:

- Maintenance activity
- User adoption
- Security history
- License compatibility

Remove unused dependencies promptly.

Update dependencies regularly.

---

# Input Validation

Validate every external input.

Examples

- Search queries
- Contact forms
- Submissions
- Reviews
- Advertisements

Use schema validation.

Recommended

Zod.

Never trust browser validation alone.

---

# Output Encoding

Escape dynamic content.

Prevent:

- Cross-Site Scripting (XSS)
- HTML injection

Avoid:

dangerouslySetInnerHTML

Unless absolutely necessary and sanitised.

---

# File Uploads

Not supported in MVP.

Future implementation should include:

- File type validation
- File size limits
- Virus scanning (where appropriate)
- Randomised filenames
- Secure object storage
- Metadata validation

Never execute uploaded content.

---

# Data Storage

Current

Static JSON.

Future

Supabase PostgreSQL.

Sensitive information should never be stored unless required by the product.

Collect only the minimum data necessary.

---

# Personal Data

Future implementations should minimise collection of:

- Names
- Email addresses
- Phone numbers
- Addresses

Collect only when there is a clear business purpose.

Provide a way to delete user data where required.

---

# Privacy

The platform should support Australian privacy requirements and be designed so it can evolve to meet additional regulatory obligations if the product expands.

Design principles:

- Data minimisation
- Purpose limitation
- Transparent data handling
- Secure storage
- Appropriate retention

---

# Logging

Never log:

- Passwords
- Access tokens
- Session cookies
- Authentication codes
- Secrets

Log:

- Errors
- Validation failures
- Security events
- Authentication events (future)

Logs should avoid exposing personal information unless operationally necessary.

---

# Session Security

Future implementation

- Secure cookies
- HttpOnly
- SameSite protection
- Short session lifetime
- Session rotation
- CSRF protection where applicable

---

# API Security

Two distinct cases:

**APIs this project exposes** to external consumers — still future scope
(`ARCHITECTURE.md`'s API Strategy). Should implement:

Authentication.

Authorisation.

Rate limiting.

Input validation.

Output validation.

Structured error responses.

Versioning.

**APIs this project consumes** (read-only, server-side — see `.ai/CONTEXT.md`'s Known
Constraints) — a narrower set of requirements, since there's no inbound consumer to defend
against:

- The API key/credential lives server-side only (environment variable, never a `NEXT_PUBLIC_`
  prefix, never referenced from a Client Component) — verify via the browser's Network tab and a
  repo-wide grep before merging, not just by reading the route handler code.
- The route handler fails gracefully on upstream errors (non-200, network failure, malformed
  response) rather than throwing an unhandled error or returning fabricated data.
- Server-side caching/revalidation (e.g. Next.js `fetch`'s `next: { revalidate }`) is used where
  the data doesn't need per-request freshness, so this project doesn't multiply load on the
  upstream API or get rate-limited/blocked by it.
- Each integration is documented per "Third-Party Services" below.

---

# Headers

Production deployments should include security headers where appropriate, such as:

- Strict-Transport-Security (HSTS)
- Content-Security-Policy (CSP)
- X-Content-Type-Options
- Referrer-Policy
- Permissions-Policy

Review header configuration as part of deployment.

---

# Content Security Policy

Adopt a restrictive Content Security Policy.

Allow only trusted origins.

Avoid:

unsafe-inline

unsafe-eval

Unless there is a documented exception.

---

# Cross-Site Scripting (XSS)

Prevent by:

- Escaping output
- Validating input
- Avoiding raw HTML rendering
- Sanitising trusted HTML if unavoidable

---

# Cross-Site Request Forgery (CSRF)

Future forms and authenticated endpoints should implement CSRF protection where required.

Evaluate framework defaults before adding custom mechanisms.

---

# SQL Injection

Current

Not applicable.

Future

Always use parameterised queries or trusted database libraries.

Never construct SQL using string concatenation.

---

# Rate Limiting

Future public APIs should implement rate limiting.

Protect:

- Login
- Search
- Contact forms
- Submissions

---

# Error Handling

Users should receive:

Friendly error messages.

Logs should contain:

Technical details.

Do not expose:

- Stack traces
- SQL errors
- Internal paths
- Environment details

---

# Third-Party Services

Before integrating any external service:

Review:

- Security
- Privacy
- Reliability
- Data processing
- Vendor reputation

Document the reason for adoption. For each third-party service integrated, record: reason for
adoption, security posture (auth method, where credentials are held), privacy impact (what data
is sent/received), reliability expectations (graceful degradation if unavailable), what data
processing it performs, and the vendor. Link the full technical detail from the relevant sprint's
notes.

---

# AI Security

Future AI features should:

- Validate prompts where appropriate.
- Avoid exposing confidential data.
- Restrict tool access.
- Log important AI operations where appropriate.
- Handle failures gracefully.

Never expose secrets to AI models.

---

# Repository Security

Protect:

Main branch.

Require:

- Pull Requests
- Code Review
- Passing CI
- Successful build
- Successful type checking

Direct commits to the main branch should be avoided.

---

# Secure Coding Standards

Engineers should:

- Follow CODING_STANDARDS.md
- Follow REVIEW_CHECKLIST.md
- Keep functions small
- Avoid hidden behaviour
- Handle failures explicitly
- Validate assumptions

---

# Security Review Checklist

Every feature should be reviewed for:

- [ ] Input validation
- [ ] Output encoding
- [ ] Error handling
- [ ] Dependency risk
- [ ] Secret exposure
- [ ] Authentication impact
- [ ] Authorisation impact
- [ ] Privacy impact
- [ ] Logging behaviour
- [ ] Third-party integrations

---

# Incident Response

If a security issue is discovered:

1. Assess severity.
2. Prevent further exposure.
3. Document the issue.
4. Fix the root cause.
5. Verify the fix.
6. Record the decision in DECISIONS.md if architectural changes are required.

Avoid making undocumented security changes.

---

# Future Security Roadmap

Version 2

- Authentication
- RBAC
- Submitter accounts

Version 3

- Admin portal
- Audit logging
- Moderation tools

Version 4

- Premium subscriptions
- Payments
- Fraud detection

Version 5

- Multi-tenant administration
- Advanced analytics
- Security monitoring

---

# Security Definition of Done

A feature is not complete until:

- Input validation is implemented where applicable.
- Error handling is appropriate.
- Secrets are protected.
- Dependencies are reviewed.
- Security implications have been considered.
- Documentation is updated when required.

---

# Guiding Principle

The safest code is often the simplest code.

Reduce unnecessary complexity.

Reduce unnecessary data collection.

Reduce unnecessary privileges.

Build systems that are easy to understand, easy to audit and easy to improve.

Security should enable trust—not create friction.