# Contributing to Maestro

Thanks for your interest in contributing. This document covers the process and expectations for contributing to Maestro.

## Getting started

1. Fork the repository
2. Clone your fork and set up the development environment:
   ```bash
   git clone https://github.com/YOUR_USERNAME/maestro.git
   cd maestro
   make setup
   ```
3. Create a branch for your work:
   ```bash
   git checkout -b your-branch-name
   ```

See the [local development guide](https://maestro.frankchan.dev/docs/installation/local-dev) for full setup instructions.

## Issues first

Every non-trivial change should start with an issue.

- **Bug fixes** - open an issue describing the bug, expected behavior, and steps to reproduce
- **Features** - open an issue describing the feature, the problem it solves, and your proposed approach
- **Refactors** - open an issue explaining what you want to change and why

Small fixes (typos, documentation corrections, one-line fixes) can go straight to a PR without an issue.

## Pull requests

### Requirements

- Every PR must reference an issue (e.g., "Fixes #123" or "Closes #123" in the PR body)
- PRs should be focused - one concern per PR
- All existing tests must pass
- New features should include tests where applicable
- Code should follow the existing patterns in the codebase

### PR process

1. Push your branch to your fork
2. Open a PR against `main`
3. Fill in the PR template with a summary, what changed, and how to test
4. Wait for review

### Commit messages

Use clear, descriptive commit messages:

```
fix: resolve 401 error when tracker API key is missing
feat: add Jira Cloud integration
docs: update getting-started with brew install
refactor: extract worker/ from agent/
```

Prefix with `fix:`, `feat:`, `docs:`, `refactor:`, `test:`, or `chore:`.

## Project structure

```
maestro/
  engine/     # Python platform - API, worker, agents, orchestrator
  ui/         # Next.js dashboard
  cli/        # Go CLI (Homebrew distribution)
  docs/       # Docusaurus documentation site
```

### Engine (Python)

- `engine/maestro/api/` - FastAPI routes
- `engine/maestro/worker/` - Worker process and job dispatch
- `engine/maestro/agents/` - Agent implementations (implementation, review, risk, deploy, monitor)
- `engine/maestro/orchestrator/` - Pipeline orchestrator
- `engine/maestro/db/` - Database models, CRUD, migrations
- `engine/maestro/external/` - GitHub, GitLab, Linear, Jira integrations

### UI (Next.js)

- `ui/src/app/` - Next.js App Router pages
- `ui/src/components/` - React components
- `ui/src/lib/` - API client, auth, utilities

### CLI (Go)

- `cli/cmd/maestro/cmd/` - Cobra commands (app, serve, worker, init, repo)

## Running tests

```bash
cd engine
uv run pytest
```

## Code style

- **Python** - follow existing patterns, use async/await, Pydantic models for API bodies
- **TypeScript** - follow existing patterns, use the existing component structure
- **Go** - standard Go conventions

No linter is enforced yet, but match the style of the surrounding code.

## Documentation

Docs live in `docs/` and are built with Docusaurus. To run locally:

```bash
cd docs
npm install
npm start
```

If your change affects user-facing behavior, update the relevant docs page.

## Questions

Open an issue with the `question` label or start a discussion in [GitHub Discussions](https://github.com/dunkinfrunkin/maestro/discussions).
