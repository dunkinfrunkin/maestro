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
# Config management
# ---------------------------------------------------------------------------

MAESTRO_HOME = Path.home() / ".maestro"
CONFIG_PATH = MAESTRO_HOME / "config.yaml"

DEFAULT_CONFIG = """\
# Maestro Configuration
# Env vars override these values. Generate with: maestro init
# Docs: https://github.com/dunkinfrunkin/maestro

server:
  host: 127.0.0.1
  port: 8000

frontend:
  port: 3000

worker:
  concurrency: 3
  poll_interval: 2.0
  mode: inline          # "inline" = agents run in API process, "queue" = workers pick up jobs

database:
  url: ""               # e.g. postgresql+asyncpg://user:pass@host:5432/db

auth:
  secret: ""            # Required. Generate with: openssl rand -hex 32
  disabled: false       # Set true to skip auth (dev only)
  oidc_issuer: ""       # e.g. https://yourcompany.okta.com/oauth2/default
  oidc_client_id: ""
  oidc_client_secret: ""

encryption:
  key: ""               # Fernet key for encrypting stored tokens

frontend_url: ""        # e.g. http://localhost:3000

# API keys (can also be set per-workspace in Settings > Models)
anthropic:
  api_key: ""

openai:
  api_key: ""
"""

# Maps config.yaml paths to env var names
_CONFIG_TO_ENV = {
    "database.url": "DATABASE_URL",
    "auth.secret": "MAESTRO_SECRET",
    "auth.disabled": "MAESTRO_AUTH_DISABLED",
    "auth.oidc_issuer": "MAESTRO_OIDC_ISSUER",
    "auth.oidc_client_id": "MAESTRO_OIDC_CLIENT_ID",
    "auth.oidc_client_secret": "MAESTRO_OIDC_CLIENT_SECRET",
    "encryption.key": "MAESTRO_ENCRYPTION_KEY",
    "frontend_url": "MAESTRO_FRONTEND_URL",
    "worker.mode": "MAESTRO_WORKER_MODE",
    "anthropic.api_key": "ANTHROPIC_API_KEY",
    "openai.api_key": "OPENAI_API_KEY",
}


def _load_config() -> dict:
    """Load config from ~/.maestro/config.yaml. Returns empty dict if not found."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        import yaml
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _get_nested(d: dict, path: str):
    """Get a nested dict value by dotted path."""
    keys = path.split(".")
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _apply_config_to_env(config: dict) -> None:
    """Set env vars from config.yaml (only if not already set)."""
    for config_path, env_var in _CONFIG_TO_ENV.items():
        if env_var in os.environ:
            continue  # env vars take priority
        value = _get_nested(config, config_path)
        if value is not None and value != "":
            os.environ[env_var] = str(value)


def _load_env_file(path: str) -> None:
    """Load environment variables from a .env file (lowest priority)."""
    env_path = Path(path)
    if not env_path.exists():
        print(f"Error: env file not found: {path}")
        sys.exit(1)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                if key not in os.environ:  # don't override existing
                    os.environ[key] = value.strip()


def _load_all_config(env_file: str | None = None) -> dict:
    """Load config with priority: env vars > config.yaml > .env file."""
    config = _load_config()
    _apply_config_to_env(config)
    if env_file:
        _load_env_file(env_file)
    return config


def _cmd_init(args: argparse.Namespace) -> None:
    """Initialize ~/.maestro/config.yaml with defaults."""
    MAESTRO_HOME.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists() and not args.force:
        print(f"Config already exists: {CONFIG_PATH}")
        print("Use --force to overwrite.")
        return
    CONFIG_PATH.write_text(DEFAULT_CONFIG)
    print(f"Created {CONFIG_PATH}")
    print("Edit the file to configure your Maestro instance.")


def _cmd_serve(args: argparse.Namespace) -> None:
    """Start the Maestro server."""
    config = _load_all_config(getattr(args, "env_file", None))
    os.environ["MAESTRO_WORKFLOW"] = args.workflow
    uvicorn.run(
        "maestro.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def _cmd_app(args: argparse.Namespace) -> None:
    """Start both backend and frontend for local development."""
    import subprocess
    import signal

    config = _load_all_config(getattr(args, "env_file", None))
    os.environ["MAESTRO_WORKFLOW"] = args.workflow
    backend_port = str(args.backend_port)
    frontend_port = str(args.frontend_port)
    os.environ.setdefault("NEXT_PUBLIC_API_URL", f"http://localhost:{backend_port}")

    procs: list[subprocess.Popen] = []

    # Find project directories
    backend_dir = Path(__file__).resolve().parent.parent
    frontend_dir = backend_dir.parent / "frontend"
    if not frontend_dir.exists():
        print(f"Error: frontend directory not found at {frontend_dir}")
        sys.exit(1)

    try:
        # Start backend
        print(f"[maestro] Starting backend on port {backend_port}...")
        backend = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "maestro.app:app",
             "--host", "127.0.0.1", "--port", backend_port, "--reload"],
            cwd=str(backend_dir),
            env=os.environ.copy(),
        )
        procs.append(backend)

        # Start frontend
        print(f"[maestro] Starting frontend on port {frontend_port}...")
        frontend_env = os.environ.copy()
        frontend_env["PORT"] = frontend_port
        frontend_env["NEXT_PUBLIC_API_URL"] = f"http://localhost:{backend_port}"
        frontend = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=str(frontend_dir),
            env=frontend_env,
        )
        procs.append(frontend)

        print(f"[maestro] App running at http://localhost:{frontend_port}")
        print(f"[maestro] API running at http://localhost:{backend_port}")
        print(f"[maestro] Press Ctrl+C to stop")

        # Wait for either to exit
        while True:
            for p in procs:
                ret = p.poll()
                if ret is not None:
                    raise KeyboardInterrupt
            import time
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[maestro] Shutting down...")
        for p in procs:
            p.send_signal(signal.SIGTERM)
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()


def _cmd_worker(args: argparse.Namespace) -> None:
    """Start the Maestro worker process."""
    config = _load_all_config(getattr(args, "env_file", None))
    import asyncio
    from maestro.agent.worker import run_worker
    asyncio.run(run_worker(
        concurrency=args.concurrency,
        poll_interval=args.poll_interval,
    ))


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

    # maestro init
    init_parser = subparsers.add_parser("init", help="Initialize ~/.maestro/config.yaml")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing config")

    # maestro serve
    serve_parser = subparsers.add_parser("serve", help="Start the Maestro server")
    serve_parser.add_argument("--env-file", help="Path to .env file to load")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    serve_parser.add_argument("--workflow", default="WORKFLOW.md", help="Path to WORKFLOW.md")

    # maestro app
    app_parser = subparsers.add_parser("app", help="Start backend + frontend for local development")
    app_parser.add_argument("--env-file", help="Path to .env file to load")
    app_parser.add_argument("--frontend-port", type=int, default=3000, help="Frontend port (default: 3000)")
    app_parser.add_argument("--backend-port", type=int, default=8000, help="Backend port (default: 8000)")
    app_parser.add_argument("--workflow", default="WORKFLOW.md", help="Path to WORKFLOW.md")

    # maestro worker
    worker_parser = subparsers.add_parser("worker", help="Start the agent worker process")
    worker_parser.add_argument("--env-file", help="Path to .env file to load")
    worker_parser.add_argument("--concurrency", type=int, default=3, help="Max concurrent agent jobs (default: 3)")
    worker_parser.add_argument("--poll-interval", type=float, default=2.0, help="Seconds between job polls (default: 2)")

    # maestro repo init
    repo_parser = subparsers.add_parser("repo", help="Repository agent configuration")
    repo_sub = repo_parser.add_subparsers(dest="repo_command")
    init_parser = repo_sub.add_parser("init", help="Scaffold .agents/ directory with template files")
    init_parser.add_argument("path", nargs="?", default=".", help="Repository path (default: current directory)")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing files")

    args = parser.parse_args(argv)

    if args.command == "init":
        _cmd_init(args)
    elif args.command == "serve":
        _cmd_serve(args)
    elif args.command == "app":
        _cmd_app(args)
    elif args.command == "worker":
        _cmd_worker(args)
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
