---
sidebar_position: 2
title: Concepts
sidebar_label: Concepts
---

# Concepts

Maestro has a few core components that work together. Understanding how they fit will help you configure and deploy effectively.

```
┌─────────────────────────────────────────────────────┐
│                     CENTCOM                          │
│         (API server + orchestrator)                  │
│                                                      │
│   Trackers ──→ Tasks ──→ Pipeline ──→ Dispatch       │
└──────────────────────┬──────────────────────────────┘
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
        ┌────────┐ ┌────────┐ ┌────────┐
        │ Worker │ │ Worker │ │ Worker │
        └───┬────┘ └───┬────┘ └───┬────┘
            │          │          │
            ▼          ▼          ▼
         Agents     Agents     Agents
         (Claude)   (Codex)    (Claude)
            │          │          │
            ▼          ▼          ▼
        ┌────────────────────────────┐
        │   Code Hosts & Trackers    │
        │  GitHub · GitLab · Linear  │
        │         · Jira             │
        └────────────────────────────┘
```
