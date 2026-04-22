---
sidebar_position: 1
title: SPECIFICATION.md
---

# SPECIFICATION.md

**Read by:** Planner, Implementer, Reviewer, QA

## Why it exists

Agentic systems like Claude Code and Codex can write code from a one-line description, but the result is generic. A specification gives agents the full picture: what problem you're solving, what the acceptance criteria are, what's explicitly out of scope, and what could go wrong. Without it, agents make assumptions about requirements that may not match your intent.

The Planner agent produces this file from issue descriptions. Other agents validate their work against it.

## What to include

- **Problem statement** - What problem does this solve? Why now? Who is affected?
- **Proposed solution** - High-level approach. What changes, what doesn't.
- **Acceptance criteria** - Concrete, testable conditions that define "done"
- **Out of scope** - What this change explicitly does NOT include (prevents agents from gold-plating)
- **Dependencies and risks** - Other systems this depends on, what could go wrong

## Example

```markdown
# Specification

## Feature: Workspace invitation emails

### Problem Statement
New workspace members have to be told their login URL verbally or over
Slack. There's no automated onboarding flow, which causes delays when
adding team members and confusion about which URL to use.

### Proposed Solution
Send an invitation email when a user is added to a workspace. The email
contains a one-time link that logs them in and redirects to the workspace
dashboard.

### Acceptance Criteria
- [ ] Adding a member to a workspace triggers an email
- [ ] Email contains a signed, expiring link (24h)
- [ ] Clicking the link logs the user in and redirects to the workspace
- [ ] Expired links show a clear error with instructions to request a new invite

### Out of Scope
- Bulk invitations
- Custom email templates
- Email provider selection (use the default SMTP config)

### Dependencies & Risks
- Requires SMTP configuration (MAESTRO_SMTP_HOST, etc.)
- Email delivery failures should not block the member addition
```
