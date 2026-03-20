"""Monitor Agent — post-deployment health checks and observability."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, query, AssistantMessage, ResultMessage

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a monitoring agent for Maestro, a coding orchestration platform.

You verify the health of a deployment after it lands. Your responsibilities:

## Immediate Health Check (0-5 minutes)
1. Verify the deployment completed successfully
   - Check latest GitHub Actions runs: `gh run list --limit 5`
   - Look for failed or in-progress workflows
2. Check application health endpoints if available
3. Review recent git log to confirm the merge landed

## Log Analysis
4. If log files or log commands are available:
   - Check for error spikes, exceptions, or panic traces
   - Compare error rates before and after deployment
   - Flag any new error patterns

## Metrics Review
5. If metrics endpoints/dashboards are configured:
   - Check response times, error rates, throughput
   - Look for anomalies or degradation
   - Compare key metrics to pre-deployment baseline

## Issue Detection
6. For each issue found, classify severity:
   - **P0**: Service down or major data loss — recommend immediate rollback
   - **P1**: Significant degradation — recommend investigation
   - **P2**: Minor issue — log for follow-up
   - **P3**: Cosmetic or non-impacting — note for awareness

## Output Format
After your checks, output a summary:
MONITOR_STATUS: HEALTHY|DEGRADED|UNHEALTHY|UNKNOWN
MONITOR_ISSUES: <count of issues found>
MONITOR_P0: <count>
MONITOR_P1: <count>
MONITOR_DETAIL: <summary of findings>

If the deployment is unhealthy (P0), recommend specific rollback steps.
If monitoring data sources are not yet configured, report what you were
able to check and note what additional monitoring connections would help.
"""


@dataclass
class MonitorResult:
    """Result of a monitoring agent run."""
    deployment_ref: str
    model: str
    status: str = "running"
    monitor_status: str = ""  # HEALTHY, DEGRADED, UNHEALTHY, UNKNOWN
    issues_found: int = 0
    p0_count: int = 0
    p1_count: int = 0
    detail: str = ""
    messages: list[dict[str, Any]] = field(default_factory=list)
    total_cost_usd: float = 0.0
    error: str | None = None


async def run_monitor_agent(
    api_key: str,
    model: str,
    workspace_path: str,
    deployment_ref: str,
    pr_title: str,
    pr_url: str | None = None,
    monitoring_endpoints: list[str] | None = None,
    log_commands: list[str] | None = None,
) -> MonitorResult:
    """Run the monitor agent for post-deployment health checks."""
    result = MonitorResult(deployment_ref=deployment_ref, model=model)

    prompt = _build_prompt(
        deployment_ref, pr_title, pr_url, monitoring_endpoints, log_commands
    )

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                model=model,
                system_prompt=SYSTEM_PROMPT,
                allowed_tools=["Bash", "Read", "Glob", "Grep"],
                cwd=workspace_path,
            ),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "text") and block.text:
                        text = block.text
                        result.messages.append({"type": "text", "text": text[:500]})
                        _parse_output(text, result)
                    elif hasattr(block, "name"):
                        result.messages.append({"type": "tool_use", "tool": block.name})

            elif isinstance(message, ResultMessage):
                result.total_cost_usd = message.total_cost_usd or 0.0
                result.status = "completed" if message.subtype == "success" else "failed"
                if message.subtype != "success":
                    result.error = message.subtype

        if result.status == "running":
            result.status = "completed"
        if not result.monitor_status:
            result.monitor_status = "UNKNOWN"

    except Exception as exc:
        logger.exception("Monitor agent failed for: %s", deployment_ref)
        result.status = "failed"
        result.error = str(exc)

    return result


def _parse_output(text: str, result: MonitorResult) -> None:
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("MONITOR_STATUS:"):
            result.monitor_status = line.split(":", 1)[1].strip()
        elif line.startswith("MONITOR_ISSUES:"):
            try:
                result.issues_found = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("MONITOR_P0:"):
            try:
                result.p0_count = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("MONITOR_P1:"):
            try:
                result.p1_count = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("MONITOR_DETAIL:"):
            result.detail = line.split(":", 1)[1].strip()


def _build_prompt(
    deployment_ref: str,
    pr_title: str,
    pr_url: str | None,
    monitoring_endpoints: list[str] | None,
    log_commands: list[str] | None,
) -> str:
    parts = [f"## Post-Deployment Monitor: {pr_title}"]
    parts.append(f"Deployment ref: {deployment_ref}")
    if pr_url:
        parts.append(f"PR: {pr_url}")

    if monitoring_endpoints:
        parts.append("\nMonitoring endpoints to check:")
        for ep in monitoring_endpoints:
            parts.append(f"  - {ep}")
    else:
        parts.append("\nNo monitoring endpoints configured yet.")

    if log_commands:
        parts.append("\nLog commands available:")
        for cmd in log_commands:
            parts.append(f"  - `{cmd}`")
    else:
        parts.append("\nNo log commands configured yet.")

    parts.append(
        "\n\nRun your post-deployment health checks. Use the tools available "
        "to check GitHub Actions status, review recent commits, and look for "
        "any signs of problems. Report your findings."
    )
    return "\n".join(parts)
