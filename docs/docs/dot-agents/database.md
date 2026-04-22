---
sidebar_position: 3
title: DATABASE.md
---

# DATABASE.md

**Read by:** Planner, Implementer, Risk

## Why it exists

Database conventions are invisible in the code until you violate them. An agent might create a table without `created_at`/`updated_at` columns, use VARCHAR instead of Text, or write a raw SQL query instead of using the ORM. These aren't bugs - the code will work - but they create inconsistencies that compound over time.

This file tells agents the rules before they write their first migration.

## What to include

- **Engine and ORM** - What database, what version, what ORM, sync or async
- **Schema overview** - Key tables, their purposes, and relationships
- **Migration strategy** - How schema changes are applied (Alembic, raw SQL, etc.)
- **Indexing** - Which indexes exist and WHY each one was created
- **Conventions** - The non-obvious rules that every table must follow

## Example

```markdown
# Database

## Engine & ORM
PostgreSQL 16 via SQLAlchemy 2.0 (async mode with asyncpg driver).

## Schema Overview
| Table | Purpose | Key Columns |
|---|---|---|
| user | User accounts | email, name, hashed_password |
| workspace | Multi-tenant container | name, slug |
| connection | Encrypted integration tokens | kind, encrypted_key |
| task_pipeline_record | Pipeline state per task | status, workspace_id |
| agent_run | Agent execution records | agent_type, status, tokens |

## Migration Strategy
Alembic with async support. Run migrations with:
alembic upgrade head

Never modify existing migrations. Always create new ones.

## Conventions
- All tables have created_at and updated_at (UTC, auto-set)
- Use Text, never VARCHAR
- Use snake_case for column names
- Foreign keys always have an index
- Soft deletes via deleted_at column, never hard delete user data
```
