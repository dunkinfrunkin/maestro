"""CLI entry point for Maestro."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn


# ---------------------------------------------------------------------------
# .agents/ template files
# ---------------------------------------------------------------------------

AGENTS_TEMPLATES: dict[str, str] = {
    "STYLE_GUIDE.md": """\
# Style Guide

> Coding conventions and patterns for this repository.
> Agents and contributors use this to write consistent code.

## Language & Framework
<!-- e.g. TypeScript / React / Next.js, Python / FastAPI, Go / Chi -->


## Naming Conventions
<!-- e.g. camelCase for variables, PascalCase for components, snake_case for API routes -->

### Files & Directories
<!-- e.g. kebab-case for files, PascalCase for component files -->

### Variables & Functions
<!-- e.g. descriptive names, no abbreviations, boolean prefixes (is/has/should) -->

### Components / Classes
<!-- e.g. PascalCase, noun-based, suffix patterns (Service, Controller, Hook) -->

## Code Style
<!-- e.g. max line length, indentation, imports ordering -->

### Formatting
<!-- e.g. Prettier config, Black, gofmt -->

### Imports
<!-- e.g. external first, then internal, group by type -->

## Patterns to Follow
<!-- e.g. prefer composition over inheritance, use hooks not HOCs -->

## Patterns to Avoid
<!-- e.g. no any types, no console.log in production, no magic numbers -->

## Error Handling
<!-- e.g. always use typed errors, never swallow exceptions -->

## Comments
<!-- e.g. only when "why" not "what", no TODO without ticket reference -->
""",
    "ARCHITECTURE.md": """\
# Architecture

> High-level system design and directory structure.
> Helps agents understand where things live and how they connect.

## Overview
<!-- Brief description of what this application does -->

## Directory Structure
```
├── src/
│   ├── ...
```
<!-- Describe key directories and their purpose -->

## Key Components
<!-- List the main modules/services and what they do -->

| Component | Location | Purpose |
|-----------|----------|---------|
|           |          |         |

## Data Flow
<!-- How does a request flow through the system? -->
<!-- e.g. Client → API Route → Service → Database -->

## External Services
<!-- List APIs, databases, queues, etc. this app talks to -->

| Service | Purpose | Docs |
|---------|---------|------|
|         |         |      |

## Environment Variables
<!-- Key env vars the app needs to run -->

| Variable | Required | Description |
|----------|----------|-------------|
|          |          |             |

## Key Design Decisions
<!-- Important architectural choices and why they were made -->
""",
    "DATABASE.md": """\
# Database

> Schema overview, key relationships, and data patterns.
> Agents reference this before writing any data-touching code.

## Database Type
<!-- e.g. PostgreSQL, MySQL, SQLite, MongoDB -->

## ORM / Query Layer
<!-- e.g. SQLAlchemy, Prisma, TypeORM, raw SQL -->

## Schema Overview
<!-- List main tables/collections and their purpose -->

| Table | Purpose | Key Columns |
|-------|---------|-------------|
|       |         |             |

## Relationships
<!-- Key foreign keys, joins, and data dependencies -->

## Migrations
<!-- How are schema changes managed? -->
<!-- e.g. Alembic, Prisma Migrate, manual SQL, create_all -->

## Indexes
<!-- Important indexes and why they exist -->

## Seed Data
<!-- How to populate the database for development -->

## Conventions
<!-- e.g. always use UUIDs, soft deletes, timestamps on every table -->

## Common Queries
<!-- Patterns for the most frequent data access operations -->
""",
    "API.md": """\
# API Conventions

> Standards for API endpoints, request/response formats, and error handling.
> Agents follow these when creating or modifying endpoints.

## Base URL
<!-- e.g. /api/v1 -->

## Authentication
<!-- e.g. Bearer token, API key header, session cookie -->

## Request Format
<!-- e.g. JSON body, Content-Type headers, query params conventions -->

## Response Format
<!-- Standard response envelope, if any -->
```json
{
  "data": {},
  "error": null
}
```

## Error Handling
<!-- Standard error response format -->
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found"
  }
}
```

## Status Codes
<!-- Which status codes to use and when -->

| Code | When to Use |
|------|-------------|
| 200  |             |
| 201  |             |
| 400  |             |
| 401  |             |
| 404  |             |
| 500  |             |

## Pagination
<!-- e.g. cursor-based, offset/limit, page/per_page -->

## Naming
<!-- e.g. plural nouns for collections, kebab-case paths -->

## Versioning
<!-- How API versions are managed -->
""",
    "TESTING.md": """\
# Testing

> How to write and run tests in this repository.
> Agents use this to write correct tests that follow project patterns.

## Test Framework
<!-- e.g. pytest, vitest, jest, go test -->

## Running Tests
```bash
# Run all tests

# Run a specific test file

# Run with coverage
```

## Test Structure
<!-- Where do tests live? -->
<!-- e.g. alongside source files, in a tests/ directory, __tests__/ -->

## Naming Conventions
<!-- e.g. test_<function_name>, describe/it blocks, *.test.ts -->

## Patterns
<!-- e.g. Arrange-Act-Assert, Given-When-Then -->

### Unit Tests
<!-- What to mock, what not to mock -->

### Integration Tests
<!-- How to set up test databases, fixtures -->

### E2E Tests
<!-- If applicable, how to run end-to-end tests -->

## Fixtures / Helpers
<!-- Common test utilities, factories, builders -->

## What to Test
<!-- e.g. all public functions, API endpoints, edge cases -->

## What NOT to Test
<!-- e.g. third-party libraries, generated code, trivial getters -->

## CI
<!-- How tests run in CI, any required env vars -->
""",
    "DEPENDENCIES.md": """\
# Dependencies

> Key libraries, why they were chosen, and what to avoid.
> Agents check this before adding new packages.

## Package Manager
<!-- e.g. npm, pnpm, yarn, pip/uv, go modules -->

## Key Dependencies

| Package | Purpose | Why This One |
|---------|---------|--------------|
|         |         |              |

## Dev Dependencies

| Package | Purpose |
|---------|---------|
|         |         |

## Rules
<!-- Guidelines for adding new dependencies -->

- [ ] Check if an existing dependency already solves the problem
- [ ] Prefer well-maintained packages with active communities
- [ ] No packages with known vulnerabilities
- [ ] Pin major versions

## Do NOT Add
<!-- Packages or categories that should be avoided -->
<!-- e.g. no lodash (use native), no moment.js (use date-fns) -->

## Updating
<!-- How to update dependencies, any special considerations -->
""",
}


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def _cmd_serve(args: argparse.Namespace) -> None:
    """Start the Maestro server."""
    os.environ["MAESTRO_WORKFLOW"] = args.workflow
    uvicorn.run(
        "maestro.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def _cmd_repo_init(args: argparse.Namespace) -> None:
    """Scaffold .agents/ directory with template files."""
    target = Path(args.path) / ".agents"
    target.mkdir(parents=True, exist_ok=True)

    created = []
    skipped = []
    for filename, content in AGENTS_TEMPLATES.items():
        filepath = target / filename
        if filepath.exists() and not args.force:
            skipped.append(filename)
            continue
        filepath.write_text(content)
        created.append(filename)

    if created:
        print(f"Created .agents/ files in {target}:")
        for f in created:
            print(f"  + {f}")
    if skipped:
        print(f"Skipped (already exist, use --force to overwrite):")
        for f in skipped:
            print(f"  - {f}")
    if not created and not skipped:
        print("Nothing to do.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="maestro",
        description="Maestro — autonomous coding agent orchestration",
    )
    subparsers = parser.add_subparsers(dest="command")

    # maestro serve
    serve_parser = subparsers.add_parser("serve", help="Start the Maestro server")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    serve_parser.add_argument("--workflow", default="WORKFLOW.md", help="Path to WORKFLOW.md")

    # maestro repo init
    repo_parser = subparsers.add_parser("repo", help="Repository agent configuration")
    repo_sub = repo_parser.add_subparsers(dest="repo_command")
    init_parser = repo_sub.add_parser("init", help="Scaffold .agents/ directory with template files")
    init_parser.add_argument("path", nargs="?", default=".", help="Repository path (default: current directory)")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing files")

    args = parser.parse_args(argv)

    if args.command == "serve":
        _cmd_serve(args)
    elif args.command == "repo" and getattr(args, "repo_command", None) == "init":
        _cmd_repo_init(args)
    else:
        # Default: if no command given, start the server (backward compat)
        if args.command is None:
            # Re-parse with serve defaults for backward compat
            parser.print_help()
            sys.exit(1)
        else:
            parser.print_help()
            sys.exit(1)


if __name__ == "__main__":
    main()
