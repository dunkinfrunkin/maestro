"""Implementation agent — uses Claude Agent SDK to code solutions for issues."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, query, AssistantMessage, ResultMessage

logger = logging.getLogger(__name__)

AVAILABLE_MODELS = [
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "description": "Best speed/intelligence balance"},
    {"id": "claude-opus-4-6", "name": "Claude Opus 4.6", "description": "Most capable, best for complex tasks"},
    {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "description": "Fastest, good for simple tasks"},
]

DEFAULT_MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are an implementation agent for Maestro, a coding orchestration platform.

You are given an issue to implement. Your job is to:
1. Understand the issue requirements
2. Read the relevant code in the repository
3. Implement the changes
4. Write or update tests if appropriate
5. Ensure the code works (run tests if available)
6. Create a git branch and commit your changes
7. Push and create a pull request

Be thorough but focused. Only change what's needed for the issue.
Follow existing code patterns and conventions in the repository.
"""


@dataclass
class AgentRun:
    """Tracks a single agent run."""
    issue_title: str
    issue_description: str
    model: str
    workspace_path: str
    status: str = "running"
    messages: list[dict[str, Any]] = field(default_factory=list)
    total_cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None


async def run_implementation_agent(
    api_key: str,
    model: str,
    workspace_path: str,
    issue_title: str,
    issue_description: str,
    repo_url: str | None = None,
) -> AgentRun:
    """Run the implementation agent on an issue.

    Args:
        api_key: Anthropic API key
        model: Model ID (e.g., claude-sonnet-4-6)
        workspace_path: Directory to work in (should be a cloned repo)
        issue_title: Issue title
        issue_description: Issue description/body
        repo_url: Optional repo URL for context
    """
    run = AgentRun(
        issue_title=issue_title,
        issue_description=issue_description,
        model=model,
        workspace_path=workspace_path,
    )

    prompt = _build_prompt(issue_title, issue_description, repo_url)

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                model=model,
                api_key=api_key,
                system_prompt=SYSTEM_PROMPT,
                allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
                cwd=workspace_path,
            ),
        ):
            if isinstance(message, AssistantMessage):
                # Track tool calls and responses
                for block in message.content:
                    if hasattr(block, "name"):
                        run.messages.append({
                            "type": "tool_use",
                            "tool": block.name,
                        })
                    elif hasattr(block, "text") and block.text:
                        run.messages.append({
                            "type": "text",
                            "text": block.text[:500],  # truncate for storage
                        })

            elif isinstance(message, ResultMessage):
                run.total_cost_usd = message.total_cost_usd or 0.0
                run.input_tokens = message.input_tokens or 0
                run.output_tokens = message.output_tokens or 0

                if message.subtype == "success":
                    run.status = "completed"
                else:
                    run.status = "failed"
                    run.error = message.subtype

        if run.status == "running":
            run.status = "completed"

    except Exception as exc:
        logger.exception("Implementation agent failed for: %s", issue_title)
        run.status = "failed"
        run.error = str(exc)

    return run


def _build_prompt(title: str, description: str, repo_url: str | None) -> str:
    parts = [f"## Issue: {title}"]
    if description:
        parts.append(f"\n{description}")
    if repo_url:
        parts.append(f"\nRepository: {repo_url}")
    parts.append(
        "\n\nPlease implement this issue. Start by exploring the codebase to understand "
        "the structure, then make the necessary changes."
    )
    return "\n".join(parts)
