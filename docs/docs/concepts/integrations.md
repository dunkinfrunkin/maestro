---
sidebar_position: 5
title: Integrations
---

# Integrations

Integrations connect Maestro to external platforms. There are two types:

## Code hosts

Code hosts are where agents write code. Maestro clones repos, creates branches, opens PRs/MRs, and posts reviews.

- **GitHub** — PRs, inline reviews, CI checks
- **GitLab** — MRs, discussions, pipelines

## Trackers

Trackers are where tasks come from. Maestro syncs issues and updates their status as work progresses.

- **GitHub Issues** — built into the GitHub integration
- **GitLab Issues** — built into the GitLab integration
- **Linear** — standalone tracker integration
- **Jira** — Cloud and Server/Data Center

## Connections

A connection is a stored, encrypted credential for an integration. Each connection has:

- A **type** (GitHub, GitLab, Linear, Jira)
- An **encrypted token** (Fernet encryption at rest)
- Optional scoping (specific repos, projects, or groups)

Connections are managed in **Settings > Connections** and belong to a workspace. Multiple connections can coexist — for example, GitHub for code + Linear for tracking.

For setup instructions, see the [Integrations guide](/docs/integrations).
