---
sidebar_position: 1
title: Homebrew
---

# Homebrew

The simplest way to install Maestro. The Homebrew formula installs a Go CLI that wraps Docker - commands like `maestro app`, `maestro serve`, and `maestro worker` automatically pull and run the Docker image.

## Install

```bash
brew install dunkinfrunkin/tap/maestro
```

## Verify

```bash
maestro version
```

## Initialize config

```bash
maestro init
```

This creates `~/.maestro/config.yaml` with sensible defaults. Edit it to add your database URL and API keys. See [Configuration](/docs/configuration) for all options.

## Run

Start the full stack (API + frontend + nginx) and a worker in two terminals:

```bash
# Terminal 1
maestro app
```

```bash
# Terminal 2
maestro worker
```

Dashboard opens at [localhost:3000](http://localhost:3000).

## How it works

The Go CLI doesn't run Maestro directly. It pulls the `ghcr.io/dunkinfrunkin/maestro` Docker image (matching the CLI version) and runs it with your environment variables passed through. This means:

- You need Docker running
- Environment variables like `ANTHROPIC_API_KEY`, `DATABASE_URL`, `MAESTRO_SECRET` are automatically forwarded to the container
- `MAESTRO_IMAGE` environment variable can override which Docker image to use

## Available commands

| Command | What it does |
|---|---|
| `maestro app` | Full stack in Docker (API + frontend + nginx) |
| `maestro serve` | API server only in Docker |
| `maestro worker` | Agent worker process in Docker |
| `maestro init` | Generate `~/.maestro/config.yaml` (local, no Docker) |
| `maestro repo init` | Scaffold `.agents/` templates (local, no Docker) |
| `maestro version` | Print version |

## Updating

```bash
brew upgrade dunkinfrunkin/tap/maestro
```
