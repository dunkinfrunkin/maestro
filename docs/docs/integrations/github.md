---
sidebar_position: 1
title: GitHub
---

# GitHub

GitHub serves as both codebase and tracker — agents open PRs, post inline reviews, and pull tasks from GitHub Issues.

## Token

Create a [personal access token](https://github.com/settings/tokens) (classic) with these scopes:

| Scope | Why |
|---|---|
| `repo` | Read/write code, open PRs, post reviews |
| `read:org` | List repositories in your organization |

Or use a [GitHub App](https://docs.github.com/en/apps) with **Repository permissions**: Contents (read/write), Pull requests (read/write), Issues (read/write), Checks (read).

## Add the connection

1. Go to **Settings > Connections**
2. Click **Add Connection** and select **GitHub**
3. Paste your token
4. Select the repositories Maestro should have access to

## What happens

- Issues from selected repos sync to the Maestro **Tasks** page
- When a task moves to **Implement**, agents clone the repo, create a branch, write code, and open a PR
- The Review Agent posts inline comments on specific lines
- The Deploy Agent verifies CI checks and merges via squash
