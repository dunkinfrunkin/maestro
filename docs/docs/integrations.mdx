---
sidebar_position: 4
title: Integrations
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

# Integrations

Maestro connects to code hosts and issue trackers. You need at least one **codebase** connection (where agents write code and open PRs) and one **tracker** connection (where tasks come from).

GitHub and GitLab can serve as both. Linear and Jira are tracker-only.

| Integration | Codebase | Tracker | What Maestro does |
|---|---|---|---|
| **GitHub** | Yes | Yes | Opens PRs, posts inline reviews, reads issues, checks CI |
| **GitLab** | Yes | Yes | Opens MRs, posts discussions, reads issues, checks pipelines |
| **Linear** | — | Yes | Syncs issues, updates status |
| **Jira** | — | Yes | Syncs issues from Cloud or Server, updates status |

All connections are configured in **Settings > Connections** from the dashboard.

---

## Setup

<Tabs>
<TabItem value="github" label="GitHub" default>

### GitHub

GitHub serves as both codebase and tracker — agents open PRs, post inline reviews, and pull tasks from GitHub Issues.

#### Token

Create a [personal access token](https://github.com/settings/tokens) (classic) with these scopes:

| Scope | Why |
|---|---|
| `repo` | Read/write code, open PRs, post reviews |
| `read:org` | List repositories in your organization |

Or use a [GitHub App](https://docs.github.com/en/apps) with **Repository permissions**: Contents (read/write), Pull requests (read/write), Issues (read/write), Checks (read).

#### Add the connection

1. Go to **Settings > Connections**
2. Click **Add Connection** and select **GitHub**
3. Paste your token
4. Select the repositories Maestro should have access to

#### What happens

- Issues from selected repos sync to the Maestro **Tasks** page
- When a task moves to **Implement**, agents clone the repo, create a branch, write code, and open a PR
- The Review Agent posts inline comments on specific lines
- The Deploy Agent verifies CI checks and merges via squash

</TabItem>
<TabItem value="gitlab" label="GitLab">

### GitLab

GitLab serves as both codebase and tracker — agents open MRs, post discussions, and pull tasks from GitLab Issues.

#### Token

Create a [personal access token](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) with these scopes:

| Scope | Why |
|---|---|
| `api` | Full API access (read/write repos, MRs, issues) |

Or use `read_api` for read-only tracker access paired with a separate codebase connection.

#### Add the connection

1. Go to **Settings > Connections**
2. Click **Add Connection** and select **GitLab**
3. Paste your token
4. Optionally set a **Group** to filter repositories (e.g. `engineering/backend`)
5. For self-managed GitLab, set the **Endpoint** (e.g. `https://gitlab.yourcompany.com`)

#### What happens

- Issues from selected projects sync to the Maestro **Tasks** page
- When a task moves to **Implement**, agents clone the repo, create a branch, write code, and open an MR
- The Review Agent posts discussions on specific lines
- The Deploy Agent checks pipelines and merges

</TabItem>
<TabItem value="linear" label="Linear">

### Linear

Linear is a tracker-only integration — Maestro syncs issues from Linear and updates their status as tasks move through the pipeline.

#### API key

Create an API key from [Linear Settings > API](https://linear.app/settings/api).

#### Add the connection

1. Go to **Settings > Connections**
2. Click **Add Connection** and select **Linear**
3. Paste your API key
4. Select the **Project** to sync issues from

#### What happens

- Issues from the selected project sync to the Maestro **Tasks** page
- Task status updates in Maestro are reflected back in Linear
- You still need a separate **GitHub** or **GitLab** connection as the codebase

</TabItem>
<TabItem value="jira" label="Jira">

### Jira

Jira is a tracker-only integration — works with both Jira Cloud and Jira Server/Data Center.

#### Token

**Jira Cloud:** Create an [API token](https://id.atlassian.com/manage-profile/security/api-tokens). You'll also need your Atlassian email.

**Jira Server/Data Center:** Create a [personal access token](https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html) (PAT). No email needed.

#### Add the connection

1. Go to **Settings > Connections**
2. Click **Add Connection** and select **Jira**
3. Set the **Base URL** (e.g. `https://yourcompany.atlassian.net` for Cloud, or `https://jira.internal.company.com` for Server)
4. Paste your API token (and email for Cloud)
5. Set the **Project Key** (e.g. `ENG`) — supports comma-separated keys for multiple projects (`ENG,PLATFORM,INFRA`)

#### What happens

- Issues from the specified project(s) sync to the Maestro **Tasks** page
- Task status updates in Maestro are reflected back in Jira
- You still need a separate **GitHub** or **GitLab** connection as the codebase

</TabItem>
</Tabs>

---

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
