"""Custom tools for agents — GitHub PR inline comments, etc."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


async def post_inline_review(
    repo: str,
    pr_number: int | str,
    comments: list[dict[str, Any]],
    verdict: str = "REQUEST_CHANGES",
    summary: str = "",
) -> dict[str, Any]:
    """Post a GitHub PR review with inline comments on specific lines.

    Args:
        repo: owner/repo
        pr_number: PR number
        comments: list of {path, line, body} dicts
        verdict: APPROVE, REQUEST_CHANGES, or COMMENT
        summary: overall review summary

    Each comment needs:
        - path: file path relative to repo root (e.g., "src/lib/api.ts")
        - line: line number in the file (not diff position)
        - body: comment text
    """
    # Map verdict to GitHub event
    event_map = {
        "APPROVE": "APPROVE",
        "REQUEST_CHANGES": "REQUEST_CHANGES",
        "COMMENT": "COMMENT",
    }
    event = event_map.get(verdict.upper(), "COMMENT")

    # Build the review payload
    # GitHub API uses `line` (absolute line in file) with `side: "RIGHT"` for new code
    review_comments = []
    for c in comments:
        comment = {
            "path": c["path"],
            "line": c["line"],
            "side": "RIGHT",
            "body": c["body"],
        }
        review_comments.append(comment)

    payload = {
        "body": summary or f"Review: {verdict}",
        "event": event,
        "comments": review_comments,
    }

    # Use gh api to post
    cmd = [
        "gh", "api",
        f"repos/{repo}/pulls/{pr_number}/reviews",
        "-X", "POST",
        "--input", "-",
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=json.dumps(payload).encode())

    if proc.returncode != 0:
        err = stderr.decode(errors="replace")
        logger.error("Failed to post inline review: %s", err)

        # Fallback: post as a regular comment if inline fails
        # (can happen if lines aren't part of the diff)
        fallback_body = summary + "\n\n"
        for c in comments:
            fallback_body += f"**{c['path']}:{c['line']}** — {c['body']}\n\n"

        fallback_cmd = [
            "gh", "pr", "review", str(pr_number),
            "--repo", repo,
            f"--{verdict.lower().replace('_', '-')}",
            "--body", fallback_body,
        ]
        proc2 = await asyncio.create_subprocess_exec(
            *fallback_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout2, stderr2 = await proc2.communicate()
        if proc2.returncode == 0:
            return {"status": "posted_as_review", "fallback": True}
        return {"status": "failed", "error": err}

    result = json.loads(stdout.decode()) if stdout else {}
    return {
        "status": "posted",
        "review_id": result.get("id"),
        "html_url": result.get("html_url", ""),
    }
