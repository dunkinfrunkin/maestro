---
sidebar_position: 6
title: SECURITY.md
---

# SECURITY.md

**Read by:** Implementer, Reviewer, Risk

## Why it exists

Security is the highest-stakes area for AI-generated code. An agent that doesn't know your auth pattern might skip middleware on a new route. An agent that doesn't know you use parameterized queries might introduce a SQL injection. The Risk Profile Agent needs to know what "secure" means in your project to score changes accurately.

This file is the security contract that all three agents enforce.

## What to include

- **Authentication** - How users authenticate (JWT, session, API key)
- **Authorization** - How permissions are enforced (RBAC, workspace scoping)
- **Secrets management** - Where secrets live, how they're accessed
- **Input validation** - How inputs are validated (Pydantic, Joi, etc.)
- **OWASP checklist** - How your project handles each top vulnerability class

## Example

```markdown
# Security

## Authentication
JWT tokens in HTTP-only cookies. Issued via OIDC/SSO flow (Okta,
Google, Azure AD). Token lifetime: 30 days, no refresh tokens.
All routes require auth except /auth/* and GET /.

## Authorization
Workspace-scoped. Users see only resources in workspaces they
belong to. Roles: owner (full access), member (read + trigger).
Every DB query filters by workspace_id.

## Secrets Management
- API keys stored with Fernet encryption (MAESTRO_ENCRYPTION_KEY)
- Never log secrets, tokens, or API keys
- Environment variables for server secrets, DB for user-provided tokens

## Input Validation
- Pydantic models for all API request bodies
- Parameterized SQL only (via SQLAlchemy ORM)
- File uploads: validate type, enforce size limit

## OWASP Checklist
- [x] Injection - parameterized queries via SQLAlchemy
- [x] Broken Auth - JWT validation on every request
- [x] Sensitive Data - Fernet encryption at rest
- [x] XSS - React auto-escapes, no dangerouslySetInnerHTML
- [x] CSRF - SameSite cookies, no CSRF tokens needed
```
