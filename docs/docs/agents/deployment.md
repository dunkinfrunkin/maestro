---
sidebar_position: 4
title: Deployment
---

# Deployment Agent

The Deployment Agent handles merging and CI verification. Unlike other agents, it does not use an LLM - it operates entirely through the code host API and CI system.

## What it does

1. Checks all CI pipeline statuses (build, lint, test, deploy-preview)
2. Waits for all checks to pass
3. Merges the PR via squash into the target branch
4. Reports success or failure back to the task
5. Optionally triggers deployment to staging and production environments

## Inputs

- PR number and URL
- CI pipeline status
- Merge target branch

## Outputs

- Merged PR (squash commit)
- Deployment trigger (if configured)
- Success/failure status

## Configuration

| Setting | Default | Description |
|---|---|---|
| merge_strategy | `squash` | `squash`, `merge`, or `rebase` |
| require_ci_pass | `true` | Block merge on CI failure |
| target_branch | `main` | Branch to merge into |
| enabled | `true` | Enable or disable this agent |

Configure per-workspace in the dashboard under **Agents > Deployment**.

This agent does not need an LLM API key. It uses the `gh` CLI or GitLab API directly.
