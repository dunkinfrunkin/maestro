"""Review Agent — thorough PR review when task moves to Review status."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, query, AssistantMessage, ResultMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior code reviewer for Maestro, a coding orchestration platform.

You are given a pull request to review. Your job is to perform a thorough code review covering:

1. **Correctness**: Does the code do what the issue/PR description says? Are there logic errors?
2. **Code Quality**: Is the code clean, readable, and following existing patterns?
3. **Tests**: Are there adequate tests? Do they cover edge cases?
4. **Security**: Are there any security vulnerabilities (injection, auth bypass, data exposure)?
5. **Performance**: Are there obvious performance issues (N+1 queries, unnecessary allocations)?
6. **Architecture**: Does the change fit well with the existing codebase architecture?

## How to review

1. Get the PR diff: `gh pr diff <number> --repo <owner/repo>`
2. Read the changed files to understand the full context
3. Identify issues with specific file paths and line numbers

## How to post inline comments

Post your review using `gh api` with inline comments on the EXACT lines:

```bash
gh api repos/OWNER/REPO/pulls/NUMBER/reviews -X POST --input - <<'EOF'
{
  "body": "Overall review summary here",
  "event": "REQUEST_CHANGES",
  "comments": [
    {"path": "src/file.ts", "line": 42, "side": "RIGHT", "body": "Issue description here"},
    {"path": "src/other.py", "line": 15, "side": "RIGHT", "body": "Another issue here"}
  ]
}
EOF
```

- `path`: file path relative to repo root
- `line`: the LINE NUMBER in the file (not the diff position)
- `side`: always use "RIGHT" (the new version of the file)
- `event`: "REQUEST_CHANGES" or "APPROVE"

IMPORTANT: The `line` must be a line that was CHANGED in the PR (appears in the diff). If commenting on an unchanged line, use a nearby changed line instead.

## Verdict

At the end of your output, include exactly one of:
REVIEW_VERDICT: APPROVE
REVIEW_VERDICT: REQUEST_CHANGES
"""


@dataclass
class ReviewResult:
    """Result of a review agent run."""
    pr_url: str
    model: str
    verdict: str = ""  # APPROVE, REQUEST_CHANGES, COMMENT
    summary: str = ""
    issues_found: int = 0
    status: str = "running"
    messages: list[dict[str, Any]] = field(default_factory=list)
    total_cost_usd: float = 0.0
    error: str | None = None


async def run_review_agent(
    api_key: str,
    model: str,
    workspace_path: str,
    pr_url: str,
    pr_title: str,
    pr_description: str,
    issue_title: str = "",
) -> ReviewResult:
    """Run the review agent on a pull request."""
    result = ReviewResult(pr_url=pr_url, model=model)

    prompt = _build_prompt(pr_url, pr_title, pr_description, issue_title)

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                model=model,
                system_prompt=SYSTEM_PROMPT,
                allowed_tools=["Read", "Bash", "Glob", "Grep"],
                cwd=workspace_path,
            ),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text") and block.text:
                        text = block.text
                        result.messages.append({"type": "text", "text": text[:500]})
                        # Parse verdict from output
                        if "APPROVE" in text and "REQUEST_CHANGES" not in text:
                            result.verdict = "APPROVE"
                        elif "REQUEST_CHANGES" in text:
                            result.verdict = "REQUEST_CHANGES"
                        elif "COMMENT" in text:
                            result.verdict = "COMMENT"
                    elif hasattr(block, "name"):
                        result.messages.append({"type": "tool_use", "tool": block.name})

            elif isinstance(message, ResultMessage):
                result.total_cost_usd = getattr(message, "total_cost_usd", 0.0) or 0.0
                result.status = "completed" if message.subtype == "success" else "failed"
                if message.subtype != "success":
                    result.error = message.subtype

        if result.status == "running":
            result.status = "completed"
        if not result.verdict:
            result.verdict = "COMMENT"

    except Exception as exc:
        logger.exception("Review agent failed for: %s", pr_url)
        result.status = "failed"
        result.error = str(exc)

    return result


def _build_prompt(pr_url: str, pr_title: str, pr_description: str, issue_title: str) -> str:
    parts = [f"## Pull Request: {pr_title}"]
    if pr_url:
        parts.append(f"URL: {pr_url}")
    if issue_title:
        parts.append(f"Related issue: {issue_title}")
    if pr_description:
        parts.append(f"\n{pr_description}")
    parts.append(
        "\n\nPlease review this PR thoroughly. Start by examining the diff "
        "(use `git diff main...HEAD` or read the changed files), then provide "
        "your review with specific file/line references."
    )
    return "\n".join(parts)
