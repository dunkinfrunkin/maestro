---
sidebar_position: 4
title: Jira
---

# Jira

Jira is a tracker-only integration — works with both Jira Cloud and Jira Server/Data Center.

You still need a separate **GitHub** or **GitLab** connection as the codebase.

## Token

**Jira Cloud:** Create an [API token](https://id.atlassian.com/manage-profile/security/api-tokens). You'll also need your Atlassian email.

**Jira Server/Data Center:** Create a [personal access token](https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html) (PAT). No email needed.

## Add the connection

1. Go to **Settings > Connections**
2. Click **Add Connection** and select **Jira**
3. Set the **Base URL** (e.g. `https://yourcompany.atlassian.net` for Cloud, or `https://jira.internal.company.com` for Server)
4. Paste your API token (and email for Cloud)
5. Set the **Project Key** (e.g. `ENG`) — supports comma-separated keys for multiple projects (`ENG,PLATFORM,INFRA`)

## What happens

- Issues from the specified project(s) sync to the Maestro **Tasks** page
- Task status updates in Maestro are reflected back in Jira
