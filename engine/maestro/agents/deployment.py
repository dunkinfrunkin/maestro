"""Deployment Agent — merges PR, monitors CI/CD, posts status updates."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, query, AssistantMessage, ResultMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a deployment agent for Maestro, a coding orchestration platform.

You are responsible for safely deploying a pull request. Follow this procedure:

## Pre-merge Checks
1. Verify all CI checks are passing (`gh pr checks`)
2. Verify the PR has required approvals
3. Check for merge conflicts
4. If any checks fail, report the failure and DO NOT proceed

## Merge
5. Merge the PR using `gh pr merge --squash` (prefer squash merge for clean history)
6. Verify the merge was successful

## Post-merge Monitoring
7. Monitor the deployment pipeline:
   - Check GitHub Actions workflow runs (`gh run list --limit 5`)
   - Wait for deployment workflows to complete
   - Report status of each workflow step
8. If deployment fails:
   - Capture the failure logs
   - Report the failure with details
   - DO NOT attempt to rollback automatically (flag for human intervention)

## Status Reporting
After each major step, output a status line in this format:
DEPLOY_STATUS: PRE_CHECK|MERGING|MERGED|DEPLOYING|SUCCESS|FAILED
DEPLOY_DETAIL: <description of current state>

If a Slack webhook URL is configured, post status updates there.
For now, just output the status lines — Slack integration will be added later.
"""


@dataclass
class DeploymentResult:
    """Result of a deployment agent run."""
    pr_url: str
    model: str
    status: str = "running"
    deploy_status: str = ""  # PRE_CHECK, MERGING, MERGED, DEPLOYING, SUCCESS, FAILED
    merged: bool = False
    deploy_detail: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    total_cost_usd: float = 0.0
    error: str | None = None


async def run_deployment_agent(
    api_key: str,
    model: str,
    workspace_path: str,
    pr_url: str,
    pr_title: str,
    pr_number: int | str,
    slack_webhook: str | None = None,
) -> DeploymentResult:
    """Run the deployment agent to merge and monitor a PR."""
    result = DeploymentResult(pr_url=pr_url, model=model)

    prompt = _build_prompt(pr_url, pr_title, pr_number, slack_webhook)

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                model=model,
                system_prompt=SYSTEM_PROMPT,
                allowed_tools=["Bash", "Read", "Glob"],
                cwd=workspace_path,
            ),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text") and block.text:
                        text = block.text
                        result.messages.append({"type": "text", "text": text})
                        _parse_output(text, result)
                    elif hasattr(block, "name"):
                        result.messages.append({"type": "tool_use", "tool": block.name})

            elif isinstance(message, ResultMessage):
                result.total_cost_usd = getattr(message, "total_cost_usd", 0.0) or 0.0
                result.status = "completed" if message.subtype == "success" else "failed"
                if message.subtype != "success":
                    result.error = message.subtype

        if result.status == "running":
            result.status = "completed"

    except Exception as exc:
        logger.exception("Deployment agent failed for: %s", pr_url)
        result.status = "failed"
        result.error = str(exc)

    return result


def _parse_output(text: str, result: DeploymentResult) -> None:
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("DEPLOY_STATUS:"):
            result.deploy_status = line.split(":", 1)[1].strip()
            if result.deploy_status == "MERGED":
                result.merged = True
        elif line.startswith("DEPLOY_DETAIL:"):
            result.deploy_detail = line.split(":", 1)[1].strip()


def _build_prompt(pr_url: str, pr_title: str, pr_number: int | str, slack_webhook: str | None) -> str:
    parts = [f"## Deploy PR: {pr_title}"]
    parts.append(f"URL: {pr_url}")
    parts.append(f"PR Number: {pr_number}")
    if slack_webhook:
        parts.append(f"Slack webhook for status updates: {slack_webhook}")
    else:
        parts.append("No Slack webhook configured — just output DEPLOY_STATUS lines.")
    parts.append(
        "\n\nProceed with the deployment procedure. Check CI status, merge the PR, "
        "and monitor the deployment pipeline."
    )
    return "\n".join(parts)
