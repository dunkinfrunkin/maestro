"""Risk Profile Agent — scores PR risk and gates deployment."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, query, AssistantMessage, ResultMessage

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Default: auto-approve anything at or below this level
DEFAULT_AUTO_APPROVE_THRESHOLD = RiskLevel.LOW

SYSTEM_PROMPT = """You are a risk assessment agent for Maestro, a coding orchestration platform.

You evaluate pull requests for deployment risk. Score each PR across these dimensions:

1. **Change Scope** (1-5): How many files/lines changed? New files vs modifications?
2. **Blast Radius** (1-5): How many users/systems could be affected if this breaks?
3. **Complexity** (1-5): How complex is the logic? Concurrency, state management, edge cases?
4. **Reversibility** (1-5): How easy is it to rollback? Data migrations = hard to reverse.
5. **Test Coverage** (1-5): Are there tests? Do they cover the changed code paths?
6. **Security Surface** (1-5): Does this touch auth, payments, PII, or external APIs?
7. **Dependency Changes** (1-5): Are dependencies added/updated/removed?

For each dimension, provide:
- Score (1 = minimal risk, 5 = very high risk)
- Brief justification

Then compute an overall risk level:
- **LOW** (avg <= 2.0): Safe for auto-deployment
- **MEDIUM** (avg <= 3.0): Recommend human review before deploy
- **HIGH** (avg <= 4.0): Requires senior review and staged rollout
- **CRITICAL** (avg > 4.0): Block deployment, requires architecture review

Output your assessment as structured text with the following format at the end:

RISK_LEVEL: LOW|MEDIUM|HIGH|CRITICAL
RISK_SCORE: <average score as float>
AUTO_APPROVE: YES|NO
SUMMARY: <one-line summary>
"""


@dataclass
class RiskProfileResult:
    """Result of a risk profile assessment."""
    pr_url: str
    model: str
    risk_level: str = ""
    risk_score: float = 0.0
    auto_approve: bool = False
    summary: str = ""
    dimensions: dict[str, Any] = field(default_factory=dict)
    status: str = "running"
    messages: list[dict[str, Any]] = field(default_factory=list)
    total_cost_usd: float = 0.0
    error: str | None = None


async def run_risk_profile_agent(
    api_key: str,
    model: str,
    workspace_path: str,
    pr_url: str,
    pr_title: str,
    pr_description: str,
    auto_approve_threshold: str = "low",
) -> RiskProfileResult:
    """Run the risk profile agent on a pull request."""
    result = RiskProfileResult(pr_url=pr_url, model=model)

    threshold = RiskLevel(auto_approve_threshold)
    threshold_order = list(RiskLevel)

    prompt = _build_prompt(pr_url, pr_title, pr_description, auto_approve_threshold)

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

        # Determine auto-approve based on threshold
        if result.risk_level:
            try:
                assessed = RiskLevel(result.risk_level.lower())
                result.auto_approve = threshold_order.index(assessed) <= threshold_order.index(threshold)
            except (ValueError, IndexError):
                result.auto_approve = False

    except Exception as exc:
        logger.exception("Risk profile agent failed for: %s", pr_url)
        result.status = "failed"
        result.error = str(exc)

    return result


def _parse_output(text: str, result: RiskProfileResult) -> None:
    """Extract structured risk data from agent output."""
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("RISK_LEVEL:"):
            result.risk_level = line.split(":", 1)[1].strip().lower()
        elif line.startswith("RISK_SCORE:"):
            try:
                result.risk_score = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("SUMMARY:"):
            result.summary = line.split(":", 1)[1].strip()


def _build_prompt(pr_url: str, pr_title: str, pr_description: str, threshold: str) -> str:
    parts = [f"## Risk Assessment: {pr_title}"]
    if pr_url:
        parts.append(f"URL: {pr_url}")
    if pr_description:
        parts.append(f"\n{pr_description}")
    parts.append(f"\nAuto-approve threshold: {threshold}")
    parts.append(
        "\n\nAnalyze this PR for deployment risk. Examine the diff, changed files, "
        "and test coverage. Provide scores for each risk dimension and an overall risk level."
    )
    return "\n".join(parts)
