---
sidebar_position: 3
title: Risk Profile
---

# Risk Profile Agent

The Risk Profile Agent assesses how risky a change is before it gets merged. It scores the PR across seven dimensions and produces an overall risk level that determines whether the change auto-merges or needs human approval.

## What it does

1. Analyzes the PR diff for complexity metrics
2. Checks which modules and dependencies are affected
3. Verifies test coverage for changed code paths
4. Scores each dimension from 1-5
5. Produces an overall risk level: **LOW**, **MEDIUM**, or **HIGH**
6. If issues are found in the diff, can send the task back to the Implementation Agent

## Seven dimensions

| Dimension | What it measures |
|---|---|
| Scope | Files and lines changed |
| Blast radius | Systems and users affected |
| Complexity | Cyclomatic complexity, new abstractions |
| Test coverage | Whether tests exist for changed paths |
| Security | Auth, crypto, PII, secrets handling |
| Reversibility | Can this be rolled back cleanly? |
| Dependencies | New or updated external packages |

## Risk levels

| Level | What happens |
|---|---|
| **LOW** | Auto-approved for merge, no human needed |
| **MEDIUM** | Requires one human approval before merge |
| **HIGH** | Requires explicit human sign-off before merge |

The auto-approve threshold is configurable per workspace.

## Inputs

- PR diff
- Changed file list and metrics
- Test results
- Dependency changes

## Outputs

- Score per dimension (1-5)
- Overall risk level (LOW / MEDIUM / HIGH)
- Risk summary with reasoning
- Optional: comments on diff if issues found

## Configuration

| Setting | Default | Description |
|---|---|---|
| model | `claude-sonnet-4-6` | LLM model for risk analysis |
| provider | `anthropic` | `anthropic` or `openai` |
| system_prompt | Built-in | Custom risk criteria |
| auto_merge_threshold | `LOW` | Maximum risk level that auto-approves |
| enabled | `true` | Enable or disable this agent |

Configure per-workspace in the dashboard under **Agents > Risk Profile**.
