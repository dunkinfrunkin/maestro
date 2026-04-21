---
sidebar_position: 6
title: Workspaces
---

# Workspaces

A workspace is a multi-tenant container that groups connections, agent configurations, and tasks together. Think of it as one team or project.

## What a workspace contains

- **Connections** — GitHub, GitLab, Linear, Jira credentials
- **Agent configs** — per-agent model selection, custom prompts, enabled/disabled state
- **API keys** — Anthropic and OpenAI keys scoped to this workspace
- **Tasks** — all issues synced from connected trackers

## Why workspaces

Workspaces let you run Maestro for multiple teams or projects from a single instance:

- **Team A** uses GitHub + Linear with Claude Sonnet
- **Team B** uses GitLab + Jira with GPT-4o
- Each team sees only their tasks and connections

## Managing workspaces

Create and manage workspaces from the dashboard. Each workspace has members with roles:

| Role | Permissions |
|---|---|
| **Owner** | Full access — connections, agents, members, settings |
| **Member** | View tasks, trigger runs, view agent logs |
