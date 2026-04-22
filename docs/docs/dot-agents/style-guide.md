---
sidebar_position: 5
title: STYLE_GUIDE.md
---

# STYLE_GUIDE.md

**Read by:** Implementer, Reviewer

## Why it exists

Code style is the most frequent source of review friction with AI agents. An agent will write perfectly correct code in a style that doesn't match your codebase - different import ordering, different naming conventions, different error handling patterns. The Review Agent then flags it, the Implementation Agent fixes it, and you've burned a review cycle on something that should have been right the first time.

This file prevents that cycle by telling both agents the rules upfront. The Implementer follows them, and the Reviewer enforces them.

## What to include

- **Language and framework** - Exact versions
- **Formatting** - Tool and config (Prettier, Black, Ruff, etc.)
- **Naming conventions** - For every element type (files, components, functions, variables, constants, DB columns)
- **Import order** - Stdlib, third-party, internal
- **Patterns to follow** - What your codebase does consistently
- **Patterns to avoid** - Anti-patterns agents must never introduce

## Example

```markdown
# Style Guide

## Language & Framework
Python 3.12 / FastAPI / SQLAlchemy 2.0 (async)
TypeScript 5 / Next.js 16 / Tailwind CSS 4

## Formatting
Backend: Ruff (ruff.toml in repo root)
Frontend: Prettier (.prettierrc)

## Naming Conventions
| Element | Convention | Example |
|---|---|---|
| Python files | snake_case | agent_runner.py |
| Python classes | PascalCase | AgentRunner |
| Python functions | snake_case | run_worker |
| TypeScript files | kebab-case | task-detail.tsx |
| React components | PascalCase | TaskDetail |
| DB columns | snake_case | created_at |
| API endpoints | plural nouns | /api/v1/workspaces |

## Import Order
1. stdlib (os, sys, asyncio)
2. third-party (fastapi, sqlalchemy)
3. internal (maestro.db, maestro.agent)

## Patterns to Follow
- All async: use async/await everywhere, never blocking I/O
- Pydantic models for all API request/response bodies
- SQLAlchemy async sessions via dependency injection

## Patterns to Avoid
- No raw SQL queries (use SQLAlchemy ORM)
- No print() for logging (use logger)
- No wildcard imports
- No mutable default arguments
```
