"""Review Agent — thorough PR review when task moves to Review status."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, query, AssistantMessage, ResultMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior code reviewer for Maestro, a coding orchestration platform.

## Review criteria
1. **Correctness**: Does the code do what the issue/PR description says?
2. **Code Quality**: Clean, readable, follows existing patterns?
3. **Tests**: Adequate test coverage?
4. **Security**: Any vulnerabilities?
5. **Performance**: Any obvious issues?

## Step-by-step procedure

### Step 1: Checkout the PR branch and read the actual code
```bash
gh pr checkout <number> --repo <owner/repo>
```
Then use the Read tool to read the changed files directly. Do NOT rely on the diff alone — read the full files.

### Step 2: Get the diff to see what changed
```bash
gh pr diff <number> --repo <owner/repo>
```
Note the exact file paths and line numbers from the diff.

### Step 3: Identify issues
For each issue, note:
- The exact file path (e.g., `src/books.js`)
- The exact line number in the NEW version of the file (count from line 1)
- Verify the line number by reading the file with the Read tool

### Step 4: Post inline comments
IMPORTANT: The `line` field must be a line that appears in the diff (was added or modified).
To find the correct line number:
1. Read the file with the Read tool — it shows line numbers (e.g., `34→  code here`)
2. Use that line number (34) in the comment

To post inline review comments, write the review JSON to a file then pass it:

```bash
# Write review JSON to temp file
cat > /tmp/review.json << 'REVIEWJSON'
{
  "body": "## Code Review Summary\n\nOverall assessment here.",
  "event": "REQUEST_CHANGES",
  "comments": [
    {
      "path": "src/books.js",
      "line": 34,
      "side": "RIGHT",
      "body": "Describe the issue and suggested fix"
    }
  ]
}
REVIEWJSON

# Post the review
gh api repos/OWNER/REPO/pulls/NUMBER/reviews -X POST --input /tmp/review.json
```

CRITICAL RULES for inline comments:
- `line` MUST be a line number that was ADDED or CHANGED in the diff (shows with + in the diff)
- `path` must match exactly what appears in the diff header (e.g., `src/router.js`)
- `side` must always be `"RIGHT"`
- If the API returns an error about the line, try a nearby changed line
- Keep comment `body` simple — no complex markdown or special characters

If approving with no issues:
```bash
echo '{"body": "LGTM!", "event": "APPROVE", "comments": []}' | gh api repos/OWNER/REPO/pulls/NUMBER/reviews -X POST --input -
```

### Step 5 (follow-up reviews only): Check previous comments, verify fixes, and resolve threads

#### 5a: Get review threads with their resolved status
```bash
gh api graphql -f query='query { repository(owner: "<OWNER>", name: "<REPO>") { pullRequest(number: <NUMBER>) { reviewThreads(first: 50) { nodes { id isResolved comments(first: 5) { nodes { body author { login } } } } } } } }'
```

#### 5b: For each UNRESOLVED thread:
1. Read the comments in the thread — look for "Fixed:" replies from the implementer
2. Read the CURRENT code to verify the fix
3. If fixed correctly: reply and RESOLVE the thread
   ```bash
   gh api repos/<owner>/<repo>/pulls/comments/<COMMENT_ID>/replies -X POST -f body="✅ Verified — fix looks good."
   gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: "<THREAD_ID>"}) { thread { isResolved } } }'
   ```
4. If NOT fixed: reply explaining what's still wrong (do NOT resolve)
   ```bash
   gh api repos/<owner>/<repo>/pulls/comments/<COMMENT_ID>/replies -X POST -f body="❌ Still not fixed: <explanation>"
   ```

The `<THREAD_ID>` is the `id` field from the reviewThreads query (starts with `PRRT_`).

The conversation thread on each comment should look like:
  - Reviewer: "Issue: ..."
  - Implementer: "Fixed: ..."
  - Reviewer: "✅ Verified" (then resolve the thread)

Always reply first, THEN resolve. The reply keeps the conversation visible.

## Verdict rules

- If ALL comments have been verified (you replied "✅ Verified") AND no new issues → REVIEW_VERDICT: APPROVE
- If ANY comment is not fixed OR you found new issues → REVIEW_VERDICT: REQUEST_CHANGES

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
