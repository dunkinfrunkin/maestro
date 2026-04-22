---
sidebar_position: 3
title: Local Development
---

# Local Development

For contributing to Maestro, debugging, or extending the platform. This installs the Python backend and Next.js frontend directly on your machine instead of using Docker.

## Prerequisites

| Requirement | Version | Purpose |
|---|---|---|
| Python | 3.12+ | Backend API |
| [uv](https://docs.astral.sh/uv/) | Latest | Python package manager |
| Node.js | 22+ | Frontend dashboard |
| Docker | Latest | PostgreSQL database |

## Setup

```bash
# Clone the repo
git clone https://github.com/dunkinfrunkin/maestro.git
cd maestro

# Start PostgreSQL
docker compose up -d

# Install everything
make install
```

`make install` runs:
- `cd engine && uv sync && uv pip install -e .` (installs the `maestro` CLI)
- `cd frontend && npm ci`

## Running

The `maestro` CLI is now available from the engine virtualenv:

```bash
# Start everything (backend + frontend)
maestro app

# Or start services individually
maestro serve --reload          # API only on :8000
maestro worker                  # Agent worker
maestro worker --concurrency 5  # Worker with custom concurrency
```

If `maestro` is not found in your PATH, either activate the venv or create a symlink:

```bash
# Option A: activate the venv
cd engine && source .venv/bin/activate

# Option B: symlink
ln -sf $(pwd)/engine/.venv/bin/maestro /opt/homebrew/bin/maestro
```

## Environment

Create a `.env.local` file in the engine directory:

```bash
cd engine
cp .env.example .env.local
```

Fill in your API keys, then load it:

```bash
set -a && source .env.local && set +a
maestro serve --reload
```

Or pass it directly:

```bash
maestro serve --env-file .env.local --reload
```

## Makefile

All common commands are available via `make`:

```bash
make setup      # Start postgres + install all deps
make app        # Start backend + frontend
make serve      # API server only (with reload)
make worker     # Agent worker process
make db         # Start PostgreSQL
make db-reset   # Nuke and restart PostgreSQL
make clean      # Remove .venv, .next, node_modules
make help       # Show all targets
```

## Configuration

Generate a default config file:

```bash
maestro init
```

This creates `~/.maestro/config.yaml`. The CLI reads ports, worker settings, and API keys from this file. See [Configuration](/docs/configuration) for all options.

## Running the docs site

```bash
cd docs
npm install
npm start
```

Opens at [localhost:3000](http://localhost:3000) (use a different port if the app is running).

## Project structure

```
maestro/
  engine/        Python FastAPI server
  frontend/       Next.js dashboard
  cli/            Go CLI (Homebrew distribution)
  docs/           Docusaurus docs site
  Dockerfile      Multi-stage production build
  Makefile        Dev shortcuts
```
