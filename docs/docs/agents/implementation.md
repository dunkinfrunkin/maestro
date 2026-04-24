---
sidebar_position: 1
title: Implementation
---

# Implementation Agent

The Implementation Agent is the workhorse of Maestro. It reads the task description, explores the codebase, writes the code, runs tests, and opens a pull request. On follow-up runs (after review feedback), it reads the comments, applies fixes, and pushes new commits.

## What it does

**First run:**

1. Reads the task description and linked issue
2. Reads `.agents/` context files if present in the repo (architecture, style guide, security rules)
3. Explores the project - structure, conventions, dependencies, existing patterns
4. Writes the implementation across new and modified files
5. Runs the existing test suite to verify nothing is broken
6. Creates a `maestro/*` branch and opens a PR on the code host
7. Attaches the PR link to the task

**Follow-up runs (after review):**

1. Rebases on the target branch (resolves conflicts if any)
2. Reads each review comment via the code host API
3. Applies the fix in code
4. Replies directly in the PR comment thread
5. Commits and force-pushes with `--force-with-lease`

## Inputs

- Issue title and description
- `.agents/` context files (ARCHITECTURE.md, STYLE_GUIDE.md, SECURITY.md, etc.)
- Clone URL and credentials for the repository
- Source files in the repository

## Outputs

- Feature branch (`maestro/{issue-id}`)
- Pull request / merge request
- Commit(s) with implementation
- PR description linking back to the issue

## Configuration

| Setting | Default | Description |
|---|---|---|
| model | `claude-sonnet-4-6` | LLM model for code generation |
| provider | `anthropic` | `anthropic` or `openai` |
| system_prompt | Built-in | Custom instructions prepended to every run |
| branch_prefix | `maestro/` | Branch naming prefix |
| enabled | `true` | Enable or disable this agent |

Configure per-workspace in the dashboard under **Agents > Implementation**.
