---
sidebar_position: 4
title: API_CONTRACTS.md
---

# API_CONTRACTS.md

**Read by:** Planner, QA

## Why it exists

When an agent adds a new endpoint, it needs to know your API conventions: how URLs are structured, how errors are returned, how pagination works, how authentication is enforced. Without this, every agent-written endpoint will be slightly different from the rest of your API, and the QA agent won't know what to validate against.

## What to include

- **Base URL and versioning** - URL prefix, versioning strategy
- **Authentication** - How requests are authenticated
- **Error format** - Standard error response shape
- **Conventions** - Naming, pagination, filtering patterns
- **Key endpoints** - Document the patterns, not an exhaustive list

## Example

```markdown
# API Contracts

## Base URL & Versioning
All endpoints under /api/v1/. Versioned via URL path.

## Authentication
Bearer JWT in Authorization header. Token from HTTP-only cookie
or explicit header. All routes require auth except /auth/* and
GET /.

## Error Format
{"detail": "Human-readable error message"}
Status codes: 400 validation, 401 unauthed, 403 forbidden, 404 not found.

## Conventions
- Resource names are plural: /workspaces, /tasks, /agents
- List endpoints return {items: [], total: int, offset: int, limit: int}
- IDs are integers in URLs: /workspaces/42
- Filters via query params: ?status=implementing&workspace_id=1
- POST for create, PUT for full update, PATCH for partial, DELETE for remove
```
