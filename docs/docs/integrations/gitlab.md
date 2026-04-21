---
sidebar_position: 2
title: GitLab
---

# GitLab

GitLab serves as both codebase and tracker - agents open MRs, post discussions, and pull tasks from GitLab Issues.

## Token

Create a [personal access token](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) with these scopes:

| Scope | Why |
|---|---|
| `api` | Full API access (read/write repos, MRs, issues) |

Or use `read_api` for read-only tracker access paired with a separate codebase connection.

## Add the connection

1. Go to **Settings > Connections**
2. Click **Add Connection** and select **GitLab**
3. Paste your token
4. Optionally set a **Group** to filter repositories (e.g. `engineering/backend`)
5. For self-managed GitLab, set the **Endpoint** (e.g. `https://gitlab.yourcompany.com`)

## What happens

- Issues from selected projects sync to the Maestro **Tasks** page
- When a task moves to **Implement**, agents clone the repo, create a branch, write code, and open an MR
- The Review Agent posts discussions on specific lines
- The Deploy Agent checks pipelines and merges
