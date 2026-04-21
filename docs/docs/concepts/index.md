---
sidebar_position: 2
title: Concepts
sidebar_label: Concepts
---

# Concepts

Maestro has a few core components that work together. Understanding how they fit will help you configure and deploy effectively.

```mermaid
graph TD
    subgraph CENTCOM["🎯 CENTCOM"]
        direction LR
        T[Trackers] --> TA[Tasks] --> P[Pipeline] --> D[Dispatch]
    end

    CENTCOM --> W1[Worker 1]
    CENTCOM --> W2[Worker 2]
    CENTCOM --> W3[Worker 3]

    W1 --> A1["🤖 Agents<br/>(Claude)"]
    W2 --> A2["🤖 Agents<br/>(Codex)"]
    W3 --> A3["🤖 Agents<br/>(Claude)"]

    A1 --> EXT
    A2 --> EXT
    A3 --> EXT

    subgraph EXT["🔌 Code Hosts & Trackers"]
        GH[GitHub]
        GL[GitLab]
        LN[Linear]
        JR[Jira]
    end
```
