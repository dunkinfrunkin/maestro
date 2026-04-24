---
sidebar_position: 2
title: Review
---

# Review Agent

The Review Agent reads pull requests and performs inline code review, posting comments on specific lines via the code host API. It operates exactly like a human reviewer - checking out the branch, reading every changed file in context, and leaving feedback directly on the diff.

## What it does

**Initial review:**

1. Checks out the PR branch
2. Checks for merge conflicts with the target branch (if conflicts: REQUEST_CHANGES immediately)
3. Reads each changed file in full context (not just the diff)
4. Analyzes for correctness, bugs, missing validation, security issues, performance problems, and style
5. When requesting changes: posts only inline comments on specific lines, no summary
6. When approving: posts only a summary comment (LGTM), no inline comments
7. Issues a verdict: **APPROVE** or **REQUEST_CHANGES**

**Verification run (after fixes):**

1. Re-reads the code at each previously commented location
2. Verifies the fix addresses the original comment
3. Replies with confirmation in the thread
4. Resolves the conversation via the code host API
5. Approves once all threads are resolved

**Approval behavior:**

The review agent's approval can be configured as soft or formal:

- `can_approve: false` (default) - posts a "LGTM" comment but does not formally approve the PR/MR
- `can_approve: true` - formally approves via the code host API

Configure in Settings > Agents > Review > extra config: `{"can_approve": true}`

## Inputs

- PR number and URL
- Changed files (full file context, not just diffs)
- `.agents/` context files (STYLE_GUIDE.md, SECURITY.md)
- CI results (if available)

## Outputs

- Inline PR comments on specific lines
- Verdict: APPROVE or REQUEST_CHANGES
- Thread replies and resolutions on follow-up

## Configuration

| Setting | Default | Description |
|---|---|---|
| model | `claude-sonnet-4-6` | LLM model for review reasoning |
| provider | `anthropic` | `anthropic` or `openai` |
| system_prompt | Built-in | Custom review criteria and style |
| severity_threshold | `suggestion` | Minimum severity to flag |
| max_comments | `20` | Maximum comments per review |
| enabled | `true` | Enable or disable this agent |

Configure per-workspace in the dashboard under **Agents > Review**.
