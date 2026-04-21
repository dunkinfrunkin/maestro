---
sidebar_position: 2
title: Concepts
sidebar_label: Concepts
---

# Concepts

Maestro has a few core components that work together. Understanding how they fit will help you configure and deploy effectively.

```mermaid
graph LR
    subgraph CENTCOM["CENTCOM"]
        T[Trackers] --> TA[Tasks] --> P[Pipeline] --> D[Dispatch]
    end

    D --> W[Workers]

    subgraph W[Workers]
        W1[Worker 1]
        W2[Worker 2]
        W3[Worker 3]
    end

    W --> A[Agents]

    subgraph A[Agents]
        IM[Implement]
        RV[Review]
        RI[Risk]
        DP[Deploy]
        MO[Monitor]
    end

    A --> I[Integrations]

    subgraph I[Integrations]
        GH[GitHub]
        GL[GitLab]
        LN[Linear]
        JR[Jira]
    end

    style CENTCOM fill:#5b4a2f,stroke:#453a28,color:#f5f0e8
    style T fill:#6b5b3e,stroke:#453a28,color:#f5f0e8
    style TA fill:#6b5b3e,stroke:#453a28,color:#f5f0e8
    style P fill:#6b5b3e,stroke:#453a28,color:#f5f0e8
    style D fill:#6b5b3e,stroke:#453a28,color:#f5f0e8

    style W fill:#2d6a4f,stroke:#1b4332,color:#f5f0e8
    style W1 fill:#40916c,stroke:#2d6a4f,color:#fff
    style W2 fill:#40916c,stroke:#2d6a4f,color:#fff
    style W3 fill:#40916c,stroke:#2d6a4f,color:#fff

    style A fill:#3a506b,stroke:#1c2541,color:#f5f0e8
    style IM fill:#5b7ea1,stroke:#3a506b,color:#fff
    style RV fill:#5b7ea1,stroke:#3a506b,color:#fff
    style RI fill:#5b7ea1,stroke:#3a506b,color:#fff
    style DP fill:#5b7ea1,stroke:#3a506b,color:#fff
    style MO fill:#5b7ea1,stroke:#3a506b,color:#fff

    style I fill:#7f4f24,stroke:#582f0e,color:#f5f0e8
    style GH fill:#b08968,stroke:#7f4f24,color:#fff
    style GL fill:#b08968,stroke:#7f4f24,color:#fff
    style LN fill:#b08968,stroke:#7f4f24,color:#fff
    style JR fill:#b08968,stroke:#7f4f24,color:#fff
```
