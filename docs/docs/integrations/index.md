---
sidebar_position: 6
title: Integrations
sidebar_label: Integrations
---

# Integrations

Maestro connects to code hosts and issue trackers. You need at least one **codebase** connection (where agents write code and open PRs) and one **tracker** connection (where tasks come from).

GitHub and GitLab can serve as both. Linear and Jira are tracker-only.

| Integration | Codebase | Tracker | What Maestro does |
|---|---|---|---|
| **GitHub** | Yes | Yes | Opens PRs, posts inline reviews, reads issues, checks CI |
| **GitLab** | Yes | Yes | Opens MRs, posts discussions, reads issues, checks pipelines |
| **Linear** | - | Yes | Syncs issues, updates status |
| **Jira** | - | Yes | Syncs issues from Cloud or Server, updates status |

All connections are configured in **Settings > Connections** from the dashboard.

## Common setups

| Setup | Codebase | Tracker | Best for |
|---|---|---|---|
| GitHub only | GitHub | GitHub Issues | Small teams, open source |
| GitLab only | GitLab | GitLab Issues | Self-hosted, all-in-one |
| GitHub + Linear | GitHub | Linear | Product-driven teams |
| GitHub + Jira | GitHub | Jira | Enterprise, existing Jira workflows |
| GitLab + Jira | GitLab | Jira | Enterprise, self-hosted stack |

## Security

All tokens are encrypted at rest using Fernet symmetric encryption before being stored in the database. Set `MAESTRO_ENCRYPTION_KEY` in your config to enable encryption. See [Configuration](/docs/configuration) for details.
