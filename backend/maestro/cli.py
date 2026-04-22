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

# ---------------------------------------------------------------------------
# AI tool instructions (prepended to each file for Claude/Cursor)
# ---------------------------------------------------------------------------

_AI_INSTRUCTIONS = """\
<!--
╔══════════════════════════════════════════════════════════════════════╗
║  INSTRUCTIONS FOR AI TOOLS (Claude, Cursor, Copilot, Codex, etc.) ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  This file is part of the Maestro agent harness. It provides         ║
║  structured context that AI agents read before executing tasks.       ║
║                                                                      ║
║  TO POPULATE THIS FILE:                                              ║
║  1. Read the existing codebase thoroughly before writing anything     ║
║  2. Replace each <!-- FILL: ... --> comment with real content         ║
║  3. Be specific — reference actual file paths, function names,       ║
║     table names, and conventions found in the code                   ║
║  4. Remove sections that don't apply to this project                 ║
║  5. Keep it concise — agents read this before every task             ║
║  6. Update when the codebase changes significantly                   ║
║                                                                      ║
║  DO NOT:                                                             ║
║  - Leave placeholder text or generic examples                        ║
║  - Include information derivable from reading the code directly      ║
║  - Add aspirational content ("we should...") — only current state    ║
║  - Duplicate information across files                                ║
║                                                                      ║
║  WHICH AGENTS READ THIS FILE:                                        ║
║  See the header below for the agent matrix (P/I/R/X/Q/D/M)          ║
╚══════════════════════════════════════════════════════════════════════╝
-->

"""

AGENTS_TEMPLATES: dict[str, str] = {
    "SPECIFICATION.md": _AI_INSTRUCTIONS + """\
# Specification

> **Agents: Planner (produces) · Implementer · Reviewer · QA (validates against)**

Detailed technical specification with acceptance criteria. The Planner agent produces
this from issue descriptions; other agents validate their work against it.

## Feature: <!-- FILL: feature name -->

### Problem Statement
<!-- FILL: What problem does this solve? Why now? Who is affected? -->

### Proposed Solution
<!-- FILL: High-level approach. What changes, what doesn\'t. -->

### Acceptance Criteria
- [ ] <!-- FILL: criterion 1 -->
- [ ] <!-- FILL: criterion 2 -->

### Out of Scope
<!-- FILL: What this change explicitly does NOT include -->

### Dependencies & Risks
<!-- FILL: Other systems this depends on. What could go wrong? -->
""",
    "ARCHITECTURE.md": _AI_INSTRUCTIONS + """\
# Architecture

> **Agents: Planner · Implementer · Reviewer · Risk**

System architecture, service boundaries, data flow, and infrastructure.

## Overview
<!-- FILL: One paragraph describing what this application does. -->

## Directory Structure
<!-- FILL: Run `find . -type d -maxdepth 3` and document what matters. -->

## Service Boundaries
| Service / Module | Responsibility | Communicates With |
|------------------|---------------|-------------------|
| <!-- FILL -->    |               |                   |

## Data Flow
<!-- FILL: Trace a typical request. Name actual files and functions. -->

## External Dependencies
| System | Protocol | Purpose | Failure Mode |
|--------|----------|---------|--------------|
| <!-- FILL --> | | | |

## Key Design Decisions
<!-- FILL: Architectural choices and WHY. Include dates if known. -->
""",
    "DATABASE.md": _AI_INSTRUCTIONS + """\
# Database

> **Agents: Planner · Implementer · Risk**

Schema definitions, migrations, relationships, and indexing strategy.

## Engine & ORM
<!-- FILL: e.g. "PostgreSQL 16 via SQLAlchemy 2.0 (async)" -->

## Schema Overview
| Table | Purpose | Key Columns | Relationships |
|-------|---------|-------------|---------------|
| <!-- FILL --> | | | |

## Migration Strategy
<!-- FILL: How schema changes are applied. -->

## Indexing
<!-- FILL: List indexes and WHY each exists. -->

## Conventions
<!-- FILL: e.g. "All tables have created_at/updated_at", "Use Text not VARCHAR" -->
""",
    "API_CONTRACTS.md": _AI_INSTRUCTIONS + """\
# API Contracts

> **Agents: Planner · QA (validates against)**

API endpoints, request/response shapes, and error codes.

## Base URL & Versioning
<!-- FILL: e.g. "/api/v1", versioned via URL path -->

## Authentication
<!-- FILL: e.g. "Bearer JWT in Authorization header" -->

## Error Format
```json
{"detail": "Human-readable error message"}
```

## Conventions
<!-- FILL: Naming, pagination, filtering patterns. -->

## Key Endpoints
<!-- FILL: Document conventions, not exhaustive listing. Link to OpenAPI if available. -->
""",
    "STYLE_GUIDE.md": _AI_INSTRUCTIONS + """\
# Style Guide

> **Agents: Implementer · Reviewer**

Code conventions, naming patterns, formatting rules, lint configuration.

## Language & Framework
<!-- FILL: e.g. "TypeScript 5 / React 19 / Next.js 16" -->

## Formatting
<!-- FILL: Tool and config. e.g. "Prettier with .prettierrc" -->

## Naming Conventions
| Element | Convention | Example |
|---------|-----------|---------|
| Files | <!-- FILL --> | <!-- FILL --> |
| Components | <!-- FILL --> | <!-- FILL --> |
| Functions | <!-- FILL --> | <!-- FILL --> |
| Variables | <!-- FILL --> | <!-- FILL --> |
| Constants | <!-- FILL --> | <!-- FILL --> |
| DB columns | <!-- FILL --> | <!-- FILL --> |

## Import Order
<!-- FILL: e.g. "1. stdlib, 2. third-party, 3. internal" -->

## Patterns to Follow
<!-- FILL: What this codebase does consistently. -->

## Patterns to Avoid
<!-- FILL: Anti-patterns agents must never introduce. -->
""",
    "SECURITY.md": _AI_INSTRUCTIONS + """\
# Security

> **Agents: Implementer · Reviewer · Risk**

Auth patterns, secrets handling, OWASP compliance, threat model.

## Authentication
<!-- FILL: How users authenticate. -->

## Authorization
<!-- FILL: How permissions are enforced. -->

## Secrets Management
<!-- FILL: Where secrets live, how accessed. Never log secrets. -->

## Input Validation
<!-- FILL: e.g. "Pydantic models for all API bodies", "Parameterized SQL only" -->

## OWASP Checklist
- [ ] Injection — <!-- FILL -->
- [ ] Broken Auth — <!-- FILL -->
- [ ] Sensitive Data Exposure — <!-- FILL -->
- [ ] XSS — <!-- FILL -->
- [ ] CSRF — <!-- FILL -->
""",
    "COMPLIANCE.md": _AI_INSTRUCTIONS + """\
# Compliance

> **Agents: Implementer · Reviewer · Risk**

Regulatory requirements, data residency, PII handling, audit rules.

## Regulatory Framework
<!-- FILL: e.g. "GDPR", "SOC 2", "HIPAA", or "None currently" -->

## PII Handling
<!-- FILL: What is PII here and how it\'s protected. -->

## Data Residency
<!-- FILL: Where data must be stored geographically. -->

## Audit Trail
<!-- FILL: What actions are logged for audit. -->

## Data Retention
<!-- FILL: How long different data types are kept. -->
""",
    "TEST_STRATEGY.md": _AI_INSTRUCTIONS + """\
# Test Strategy

> **Agents: QA (primary)**

Testing philosophy, coverage targets, test types, fixture conventions.

## Framework
<!-- FILL: e.g. "pytest", "vitest", "Playwright" -->

## Running Tests
```bash
# FILL: exact commands
```

## Test Types
| Type | Location | Coverage Target | When to Write |
|------|----------|----------------|---------------|
| Unit | <!-- FILL --> | <!-- FILL --> | <!-- FILL --> |
| Integration | <!-- FILL --> | <!-- FILL --> | <!-- FILL --> |
| E2E | <!-- FILL --> | <!-- FILL --> | <!-- FILL --> |

## What to Test / What NOT to Test
<!-- FILL: Concrete guidance. -->

## Fixtures & Helpers
<!-- FILL: Common test utilities available. -->
""",
    "RUNBOOK.md": _AI_INSTRUCTIONS + """\
# Runbook

> **Agents: Risk · Deploy · Monitor**

Operational procedures, incident response, escalation paths.

## Health Checks
<!-- FILL: How to verify the system is healthy. -->

## Common Issues
| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| <!-- FILL --> | | |

## Incident Response
<!-- FILL: Step-by-step procedure. -->

## Escalation
<!-- FILL: Who to contact and when. -->

## Rollback Procedure
<!-- FILL: How to roll back a bad deploy. -->
""",
    "DEPLOY.md": _AI_INSTRUCTIONS + """\
# Deploy

> **Agents: Deploy (primary)**

Deploy strategies, environments, rollout configs, feature flags.

## Environments
| Environment | URL | Purpose | Deploy Trigger |
|-------------|-----|---------|---------------|
| <!-- FILL --> | | | |

## Deploy Process
<!-- FILL: Step-by-step. -->

## CI/CD Pipeline
<!-- FILL: What checks must pass. How deploy is triggered. -->

## Feature Flags
<!-- FILL: How feature flags work, if applicable. -->

## Required Secrets
<!-- FILL: Secret names needed for deploy (not values). -->
""",
    "MONITORING.md": _AI_INSTRUCTIONS + """\
# Monitoring

> **Agents: Monitor (primary)**

Dashboards, alert thresholds, SLOs, baseline metrics.

## Key Metrics
| Metric | Baseline | Alert Threshold | Dashboard |
|--------|----------|----------------|-----------|
| <!-- FILL --> | | | |

## SLOs
<!-- FILL: e.g. "99.9% uptime", "p95 < 300ms" -->

## Dashboards
<!-- FILL: Where to find them. -->

## Alerting
<!-- FILL: How alerts work and who gets them. -->

## Post-Deploy Monitoring
<!-- FILL: What to watch after a deploy. -->
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
    host = args.host or _get_nested(config, "server.host") or "127.0.0.1"
    port = args.port or _get_nested(config, "server.port") or 8000
    uvicorn.run(
        "maestro.app:app",
        host=host,
        port=int(port),
        reload=args.reload,
    )


def _cmd_app(args: argparse.Namespace) -> None:
    """Start both backend and frontend for local development."""
    import subprocess
    import signal

    config = _load_all_config(getattr(args, "env_file", None))
    backend_port = str(args.backend_port or _get_nested(config, "server.port") or 8000)
    frontend_port = str(args.frontend_port or _get_nested(config, "frontend.port") or 3000)
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
    concurrency = args.concurrency or _get_nested(config, "worker.concurrency") or 3
    poll_interval = args.poll_interval or _get_nested(config, "worker.poll_interval") or 2.0
    import asyncio
    from maestro.worker.worker import run_worker
    asyncio.run(run_worker(
        concurrency=int(concurrency),
        poll_interval=float(poll_interval),
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
    serve_parser.add_argument("--host", default=None, help="Bind host (default: config or 127.0.0.1)")
    serve_parser.add_argument("--port", type=int, default=None, help="Bind port (default: config or 8000)")
    serve_parser.add_argument("--reload", action="store_true", help="Enable auto-reload")

    # maestro app
    app_parser = subparsers.add_parser("app", help="Start backend + frontend for local development")
    app_parser.add_argument("--env-file", help="Path to .env file to load")
    app_parser.add_argument("--frontend-port", type=int, default=None, help="Frontend port (default: config or 3000)")
    app_parser.add_argument("--backend-port", type=int, default=None, help="Backend port (default: config or 8000)")

    # maestro worker
    worker_parser = subparsers.add_parser("worker", help="Start the agent worker process")
    worker_parser.add_argument("--env-file", help="Path to .env file to load")
    worker_parser.add_argument("--concurrency", type=int, default=None, help="Max concurrent agent jobs (default: config or 3)")
    worker_parser.add_argument("--poll-interval", type=float, default=None, help="Seconds between job polls (default: config or 2.0)")

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
