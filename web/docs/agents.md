---
sidebar_position: 3
title: Agents
---

# Agents

Maestro uses specialized agents for each stage of the pipeline. Each agent has its own system prompt, model configuration, and execution logic.

## Implementation Agent

**Purpose:** Write code to fulfill the task requirements.

**How it works:**
1. Reads the task description and any linked issues
2. Explores the project codebase to understand structure, conventions, and patterns
3. Writes the implementation — new files, modified files, tests
4. Creates a Git branch and opens a pull request
5. Attaches code snippets and file paths to the task activity log

**Configuration:**
- `model` — which LLM to use (default: Claude)
- `system_prompt` — custom instructions for the agent
- `max_file_reads` — limit on how many files the agent can read per run
- `branch_prefix` — prefix for created branches (default: `maestro/`)

## Review Agent

**Purpose:** Perform inline code review on pull requests.

**How it works:**
1. Fetches the PR diff from GitHub
2. Reads each changed file in context
3. Leaves inline comments on specific lines where issues are found
4. Comments are categorized: `bug`, `style`, `performance`, `security`, `suggestion`
5. If no issues found, approves the review

**Configuration:**
- `model` — which LLM to use
- `system_prompt` — review criteria and style guidelines
- `severity_threshold` — minimum severity to flag (default: `suggestion`)
- `max_comments` — cap on number of comments per review

## Risk Profile Agent

**Purpose:** Assess the risk of merging a change.

**How it works:**
1. Analyzes the PR diff for complexity metrics
2. Checks which modules and dependencies are affected (blast radius)
3. Verifies test coverage for changed code
4. Produces a risk score: `LOW`, `MEDIUM`, or `HIGH`
5. `LOW` risk tasks proceed automatically; `MEDIUM` and `HIGH` require human approval

**Configuration:**
- `model` — which LLM to use
- `system_prompt` — risk assessment criteria
- `auto_merge_threshold` — risk level that can auto-merge (default: `LOW`)

## Deployment Agent

**Purpose:** Merge pull requests and monitor CI.

**How it works:**
1. Merges the approved PR into the target branch
2. Monitors CI pipeline status (GitHub Actions, etc.)
3. Reports success or failure
4. On failure, attaches CI logs to the task

**Configuration:**
- `merge_strategy` — `squash`, `merge`, or `rebase` (default: `squash`)
- `require_ci_pass` — wait for CI before marking as deployed (default: `true`)
- `target_branch` — branch to merge into (default: `main`)

## Monitor Agent

**Purpose:** Post-deployment health monitoring.

**How it works:**
1. Watches application logs and error rates after deployment
2. Compares error rates to pre-deployment baseline
3. Flags anomalies if error rates spike
4. Can trigger rollback alerts

**Configuration:**
- `monitoring_window` — how long to watch after deploy (default: `30m`)
- `error_threshold` — percentage increase that triggers an alert (default: `50%`)
- `log_sources` — which log streams to watch

## Custom agents

You can create custom agents using the plugin framework. See [Plugins](/docs/plugins) for details.
