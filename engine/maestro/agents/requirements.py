"""Requirements Agent — conversational agent that clarifies and finalizes ticket requirements."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from maestro.db.engine import get_session
from maestro.db.models import AgentRunLog

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """You are a requirements analyst helping a software team clarify and finalize ticket requirements.

Your goal is to:
1. Review the existing ticket title and description
2. Ask targeted clarifying questions to fill in gaps (acceptance criteria, edge cases, scope boundaries, technical constraints)
3. Once you have enough information, produce a finalized, well-structured ticket description

## Rules
- Ask ONE question at a time. Do not ask multiple questions in one message.
- Keep questions concise and specific.
- When you have gathered sufficient information to write a complete description, finalize.

## Response protocol
Every response MUST end with exactly one of the following:

If you have another question:
QUESTION: <your single question here>

If you are ready to finalize (you have enough info):
REQUIREMENTS_FINAL: YES
UPDATED_DESCRIPTION:
<full updated ticket description in markdown, including a clear summary, acceptance criteria as a checklist, and any relevant technical notes>
"""


# Alias used by the GET /agents/{agent_type}/default-prompt endpoint
SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT


@dataclass
class RequirementsResult:
    status: str = "completed"
    updated_description: str = ""
    total_cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None
    messages: list[dict[str, Any]] = field(default_factory=list)


async def _write_log(run_id: int, entry_type: str, content: str) -> None:
    try:
        async with get_session() as session:
            log = AgentRunLog(
                agent_run_id=run_id,
                entry_type=entry_type,
                content=content,
            )
            session.add(log)
            await session.commit()
    except Exception:
        logger.exception("Failed to write requirements agent log")


async def _wait_for_user_prompt(
    run_id: int,
    after_id: int,
    timeout_s: float = 86400.0,
) -> str | None:
    """Poll agent_run_logs for a user_prompt entry newer than after_id. Returns content or None on timeout."""
    from sqlalchemy import select as sa_select
    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(3)
        try:
            async with get_session() as session:
                row = await session.scalar(
                    sa_select(AgentRunLog)
                    .where(
                        AgentRunLog.agent_run_id == run_id,
                        AgentRunLog.entry_type == "user_prompt",
                        AgentRunLog.id > after_id,
                    )
                    .order_by(AgentRunLog.id)
                    .limit(1)
                )
                if row:
                    return row.content
        except Exception:
            logger.exception("Error polling for user prompt")
    return None


def _get_last_log_id(run_id: int) -> int:
    """Synchronous helper — not used; we track IDs explicitly in the loop."""
    return 0


async def _get_current_max_log_id(run_id: int) -> int:
    """Return the current highest log id for this run."""
    from sqlalchemy import select as sa_select, func
    try:
        async with get_session() as session:
            result = await session.scalar(
                sa_select(func.max(AgentRunLog.id)).where(
                    AgentRunLog.agent_run_id == run_id
                )
            )
            return result or 0
    except Exception:
        return 0


async def run_requirements_agent(
    run_id: int,
    issue_title: str,
    issue_description: str,
    issue_identifier: str,
    system_prompt: str,
    api_key: str,
    model: str,
) -> RequirementsResult:
    """Run the requirements agent — conversational loop using ClaudeSDKClient."""
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, AssistantMessage, ResultMessage

    result = RequirementsResult()

    await _write_log(run_id, "status", f"Requirements agent starting for {issue_identifier}")

    initial_prompt = f"## Ticket: {issue_title}\n\n{issue_description or '(No description yet)'}\n\nPlease review this ticket and begin clarifying the requirements."

    env_overrides = {"ANTHROPIC_API_KEY": api_key}

    options = ClaudeAgentOptions(
        model=model,
        system_prompt=system_prompt,
        allowed_tools=[],
    )

    import os
    old_key = os.environ.get("ANTHROPIC_API_KEY")
    os.environ["ANTHROPIC_API_KEY"] = api_key

    try:
        client = ClaudeSDKClient(options)
        await client.connect(initial_prompt)

        while True:
            # Collect the full response text from this turn
            response_text = ""
            async for message in client.receive_messages():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if hasattr(block, "text") and block.text:
                            response_text += block.text
                            result.messages.append({"type": "text", "text": block.text})
                elif isinstance(message, ResultMessage):
                    result.total_cost_usd += getattr(message, "total_cost_usd", 0.0) or 0.0
                    result.input_tokens += getattr(message, "input_tokens", 0) or 0
                    result.output_tokens += getattr(message, "output_tokens", 0) or 0
                    break  # end of this turn

            # Log the full assistant response
            if response_text.strip():
                await _write_log(run_id, "text", response_text.strip())

            # Check for finalization
            if "REQUIREMENTS_FINAL: YES" in response_text:
                match = re.search(r"UPDATED_DESCRIPTION:\s*\n(.*)", response_text, re.DOTALL)
                if match:
                    result.updated_description = match.group(1).strip()
                else:
                    result.updated_description = issue_description
                await _write_log(run_id, "status", "Requirements finalized")
                break

            # Check for a question
            q_match = re.search(r"QUESTION:\s*(.+?)(?:\n|$)", response_text)
            if q_match:
                question_text = q_match.group(1).strip()
                await _write_log(run_id, "question", question_text)

                # Record last log id so we only look for NEW user_prompts
                last_id = await _get_current_max_log_id(run_id)

                user_response = await _wait_for_user_prompt(run_id, last_id)
                if user_response is None:
                    await _write_log(run_id, "status", "Timed out waiting for user response — finalizing with current info")
                    result.updated_description = issue_description
                    break

                await _write_log(run_id, "user_prompt", user_response)
                await client.query(user_response)
            else:
                # Agent responded without the expected protocol — treat as finalization
                await _write_log(run_id, "status", "Agent completed without explicit finalization marker")
                result.updated_description = response_text.strip() or issue_description
                break

        await client.disconnect()

    except Exception as exc:
        logger.exception("Requirements agent error for run %d", run_id)
        result.status = "failed"
        result.error = str(exc)
        await _write_log(run_id, "error", f"Requirements agent error: {exc}")
    finally:
        if old_key is not None:
            os.environ["ANTHROPIC_API_KEY"] = old_key
        elif "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

    return result
