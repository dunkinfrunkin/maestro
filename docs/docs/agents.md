---
sidebar_position: 4
title: Agents
---

# Agents

Maestro uses five specialized agents, each responsible for one stage of the pipeline. Every agent runs as a Claude Code CLI subprocess with access to Read, Write, Edit, Bash, Glob, and Grep tools.

## Implementation Agent

Writes code to fulfill task requirements.

**What it does:**
1. Reads the task description and linked issues
2. Explores the project codebase - structure, conventions, patterns
3. Writes the implementation (new files, modified files, tests)
4. Runs the test suite
5. Creates a branch and opens a pull request

**On follow-up runs** (after review comments):
1. Reads each review comment via `gh api`
2. Applies the fix in code
3. Replies directly in the PR comment thread
4. Pushes the commit

**Configuration:**

| Setting | Default | Description |
|---|---|---|
| `model` | `claude-sonnet-4-6` | LLM model |
| `system_prompt` | Built-in | Custom instructions |
| `branch_prefix` | `maestro/` | Branch naming prefix |

## Review Agent

Performs inline code review on pull requests.

**What it does:**
1. Checks out the PR branch
2. Reads each changed file in full context
3. Posts inline comments on specific lines via GitHub API
4. Categorizes comments: `bug`, `style`, `performance`, `security`, `suggestion`
5. Issues a verdict: `APPROVE` or `REQUEST_CHANGES`

**On verification runs** (after fixes are pushed):
1. Re-reads the code at each commented location
2. Verifies the fix addresses the comment
3. Replies with confirmation in the thread
4. Resolves the conversation via GitHub GraphQL API
5. Approves once all threads are resolved

**Configuration:**

| Setting | Default | Description |
|---|---|---|
| `model` | `claude-sonnet-4-6` | LLM model |
| `system_prompt` | Built-in | Review criteria and style |
| `severity_threshold` | `suggestion` | Minimum severity to flag |
| `max_comments` | `20` | Cap per review |

## Risk Profile Agent

Assesses the risk of merging a change across seven dimensions.

**What it does:**
1. Analyzes the PR diff for complexity metrics
2. Checks which modules and dependencies are affected
3. Verifies test coverage for changed code
4. Produces a score for each dimension (1-5)
5. Outputs an overall risk level: `LOW`, `MEDIUM`, or `HIGH`

**Configuration:**

| Setting | Default | Description |
|---|---|---|
| `model` | `claude-sonnet-4-6` | LLM model |
| `system_prompt` | Built-in | Risk criteria |
| `auto_merge_threshold` | `LOW` | Max risk that auto-approves |

## Deployment Agent

Merges pull requests after verifying CI.

**What it does:**
1. Checks all GitHub Actions pipeline statuses
2. Waits for all checks to pass (build, lint, test, deploy-preview)
3. Merges the PR into the target branch
4. Reports success or failure to the task

**Configuration:**

| Setting | Default | Description |
|---|---|---|
| `merge_strategy` | `squash` | `squash`, `merge`, or `rebase` |
| `require_ci_pass` | `true` | Block merge on CI failure |
| `target_branch` | `main` | Branch to merge into |

## Monitor Agent

Watches for regressions after deployment.

**What it does:**
1. Queries Datadog for latency (p99) and error rate changes
2. Queries Splunk logs for new exceptions
3. Monitors for 15 minutes after deploy
4. Flags the task if anomalies are detected

**Configuration:**

| Setting | Default | Description |
|---|---|---|
| `monitoring_window` | `15m` | Duration to watch after deploy |
| `error_threshold` | `50%` | Error rate increase that triggers alert |
| `log_sources` | `datadog,splunk` | Which systems to query |

## Custom agents

You can create custom agents using the plugin framework. See [Plugins](/docs/plugins) for details.
