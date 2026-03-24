---
sidebar_position: 1
title: Philosophy
---

# Philosophy

Maestro is built on a set of principles about how software should be built when agents handle the software lifecycle. These ideas are influenced by what teams are learning as they shift from writing code to designing systems where agents can do reliable work.

## Humans steer. Agents execute.

Engineers define intent, set constraints, and review outcomes. Agents handle the implementation, review, testing, and deployment. The bottleneck shifts from writing code to designing environments where agents can do reliable work.

When something fails, the fix is almost never "try harder." The right question is always: what capability is missing, and how do we make it legible and enforceable for the agent?

## Every agent gets its own role

A single monolithic agent can't hold the full context of implementation, review, risk assessment, and deployment. Maestro decomposes the pipeline into dedicated agents — Implementation, Review, Risk Profile, Deployment, and Monitor — each with a focused system prompt, clear inputs, and a single responsibility.

This mirrors how effective engineering organizations work. You don't ask one person to write the code, review it, assess the risk, and monitor the deploy. Separation of concerns applies to agents just as well as it applies to code.

## Agents talk through the same tools humans use

Review comments, PR threads, CI checks, GitHub API calls. Agents don't use special channels. They post inline comments on specific lines of code, reply in threads, resolve conversations, and approve pull requests — the same workflow as human developers.

This has a practical consequence: you can read the PR history and understand what happened, whether the author was a person or an agent. There is no separate agent log you need to consult. The pull request is the record.

## Corrections are cheap. Waiting is expensive.

In high-throughput agent systems, the cost of a follow-up fix is almost always lower than the cost of blocking progress. Maestro favors fast iteration over gated perfection.

Review agents catch issues. Implementation agents fix them. The loop continues. This would be irresponsible in a low-throughput environment. In a system where agent throughput far exceeds human attention, it is often the right tradeoff.

## Risk is scored, not assumed

Not every change needs a human in the loop. And not every change should be auto-approved.

Maestro scores each PR across seven dimensions:

| Dimension | What it measures |
|-----------|-----------------|
| Scope | Number of files and lines changed |
| Blast radius | How many systems or users are affected |
| Complexity | Cyclomatic complexity, new abstractions |
| Test coverage | Whether tests exist for changed paths |
| Security | Auth, crypto, PII, secrets handling |
| Reversibility | Can this be rolled back cleanly? |
| Dependencies | New or updated external dependencies |

Low-risk changes auto-approve. Medium and above escalate to a human reviewer. The threshold is configurable per workspace.

## Observability is not optional

Deploying code is not the finish line. Maestro's Monitor agent checks Datadog dashboards and Splunk logs for 15 minutes after every deploy. If latency spikes or error rates climb, it flags the change.

Deploy confidence comes from automated post-deploy verification, not hope.

## The pipeline is the product

These principles aren't abstract. They are encoded directly into the pipeline:

```
Issue → Implement → Review ↔ Fix → Risk Profile → Deploy → Monitor
```

Each transition is an explicit handoff from one agent to the next. Each agent has its own system prompt, model selection, and configuration. The pipeline is visible, auditable, and configurable — not a black box.

This is what we mean by harness engineering: building the scaffolding that makes agents effective, rather than writing the code yourself.
