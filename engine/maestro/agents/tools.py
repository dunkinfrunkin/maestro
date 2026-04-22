"""Backwards-compatible re-export — use maestro.external.github.codehost instead.

The post_inline_review function is preserved for existing callers but
delegates to GitHubCodeHost internally.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def post_inline_review(
    repo: str,
    pr_number: int | str,
    comments: list[dict[str, Any]],
    verdict: str = "REQUEST_CHANGES",
    summary: str = "",
) -> dict[str, Any]:
    """Post a GitHub PR review with inline comments.

    This is a backwards-compatible wrapper. New code should use
    GitHubCodeHost.create_review() directly.
    """
    # Lazy import to avoid circular deps
    from maestro.external.github.codehost import GitHubCodeHost
    import os

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")
    if not token:
        logger.error("No GITHUB_TOKEN or GH_TOKEN in environment")
        return {"status": "failed", "error": "no token"}

    codehost = GitHubCodeHost(token=token)
    try:
        result = await codehost.create_review(
            repo=repo,
            pr_number=int(pr_number),
            comments=comments,
            verdict=verdict,
            summary=summary,
        )
        return {
            "status": result.status,
            "review_id": result.review_id,
            "html_url": result.html_url,
            "error": result.error,
        }
    finally:
        await codehost.close()
