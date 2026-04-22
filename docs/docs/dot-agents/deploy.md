---
sidebar_position: 10
title: DEPLOY.md
---

# DEPLOY.md

**Read by:** Deploy

## Why it exists

The Deployment Agent needs to know your deployment process: what environments exist, what CI checks must pass, how deploys are triggered, and what secrets are needed. Without this, the agent can't verify that a change is safe to merge or know whether CI failures are blocking.

## What to include

- **Environments** - What environments exist and how they're accessed
- **Deploy process** - Step-by-step from merged PR to production
- **CI/CD pipeline** - What checks must pass before merge
- **Feature flags** - How feature flags work, if applicable
- **Required secrets** - Secret names (not values) needed for deploy

## Example

```markdown
# Deploy

## Environments
| Environment | URL | Deploy trigger |
|---|---|---|
| Staging | staging.maestro.dev | Push to main |
| Production | maestro.frankchan.dev | Git tag v* |

## Deploy Process
1. PR merged to main via squash
2. GitHub Actions builds Docker image
3. Image pushed to GHCR
4. Staging auto-deploys from main
5. Production deploys on version tag

## CI Checks (must pass before merge)
- Build: go build, uv sync
- Lint: ruff check, eslint
- Test: pytest, npm test
- Docker: multi-arch build succeeds

## Required Secrets
- ANTHROPIC_API_KEY (agent execution)
- HOMEBREW_TAP_TOKEN (formula updates)
- GHCR credentials (Docker push)
```
