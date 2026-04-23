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
2. Thoroughly explore the repository to understand the existing codebase, patterns, and relevant context — this is your primary source of truth
3. Only if critical context is still missing after exploring the repo, use the Atlas CLI to check sources like GitLab, Slack, or Glean
4. Ask targeted clarifying questions to fill in remaining gaps (acceptance criteria, edge cases, scope boundaries, technical constraints)
5. Once you have enough information, produce a finalized, well-structured ticket description

## Rules
- Always start by exploring the repo: read relevant files, search for related code, understand existing patterns. Do this thoroughly before considering any other source.
- Only reach for the Atlas CLI if the repo alone leaves critical questions unanswered — it should be a last resort, not a first step.
- Only ask ONE question at a time after exhausting automated investigation.
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


async def _run_turn(
    conversation: list[dict[str, Any]],
    system_prompt: str,
    model: str,
    api_key: str,
    run_id: int,
    cwd: str,
) -> tuple[str, float, int, int]:
    """Run one Claude CLI turn with the full conversation history encoded in the prompt."""
    from maestro.agents.cli_runner import run_cli_with_logging

    # Encode full conversation history into a single prompt string
    history_parts = []
    for msg in conversation:
        prefix = "USER" if msg["role"] == "user" else "ASSISTANT"
        history_parts.append(f"{prefix}:\n{msg['content']}")
    prompt = "\n\n---\n\n".join(history_parts)

    result = await run_cli_with_logging(
        run_id=run_id,
        system_prompt=system_prompt,
        prompt=prompt,
        provider="anthropic",
        model=model,
        workspace_path=cwd,
        allowed_tools=["Bash", "Read", "Glob", "Grep"],
        api_key=api_key,
        log_text=False,
    )

    return (
        result.get("all_text", "").strip(),
        result.get("total_cost_usd", 0.0) or 0.0,
        result.get("input_tokens", 0) or 0,
        result.get("output_tokens", 0) or 0,
    )


async def run_requirements_agent(
    run_id: int,
    issue_title: str,
    issue_description: str,
    issue_identifier: str,
    system_prompt: str,
    api_key: str,
    model: str,
    cwd: str | None = None,
    allowed_tools: list[str] | None = None,
) -> RequirementsResult:
    """Run the requirements agent — conversational loop using per-turn claude CLI calls."""
    import os
    _cwd = cwd or os.path.expanduser("~")

    result = RequirementsResult()

    await _write_log(run_id, "status", f"Requirements agent starting for {issue_identifier}")

    initial_user_message = (
        f"## Ticket: {issue_title}\n\n"
        f"{issue_description or '(No description yet)'}\n\n"
        f"Please review this ticket and begin clarifying the requirements."
    )

    # conversation holds the full history as alternating user/assistant messages
    conversation: list[dict[str, Any]] = [{"role": "user", "content": initial_user_message}]

    try:
        while True:
            await _write_log(run_id, "status", "Thinking...")

            response_text, cost, in_tok, out_tok = await _run_turn(
                conversation, system_prompt, model, api_key, run_id, _cwd
            )

            result.total_cost_usd += cost
            result.input_tokens += in_tok
            result.output_tokens += out_tok

            if not response_text.strip():
                await _write_log(run_id, "error", "Empty response from agent")
                result.status = "failed"
                break

            conversation.append({"role": "assistant", "content": response_text})
            result.messages.append({"type": "text", "text": response_text})

            # Check for finalization
            if "REQUIREMENTS_FINAL: YES" in response_text:
                preamble = re.split(r"\n*REQUIREMENTS_FINAL:", response_text)[0].strip()
                if preamble:
                    await _write_log(run_id, "text", preamble)
                match = re.search(r"UPDATED_DESCRIPTION:\s*\n(.*)", response_text, re.DOTALL)
                proposed = match.group(1).strip() if match else issue_description

                # Show the proposed description and ask for confirmation before writing to JIRA
                await _write_log(run_id, "text", f"**Proposed updated description:**\n\n{proposed}")
                await _write_log(run_id, "question", "Does this look good? Reply with any adjustments, or say 'yes' / 'looks good' to write this to the ticket.")

                last_id = await _get_current_max_log_id(run_id)
                user_response = await _wait_for_user_prompt(run_id, last_id)
                if user_response is None:
                    await _write_log(run_id, "status", "Timed out waiting for confirmation — requirements not written to ticket")
                    result.updated_description = ""
                    break

                _affirmative = {"yes", "y", "lgtm", "looks good", "ship it", "ok", "okay", "approve", "approved", "confirmed", "confirm"}
                if user_response.strip().lower() in _affirmative:
                    result.updated_description = proposed
                    await _write_log(run_id, "status", "Requirements finalized")
                else:
                    # User wants changes — feed their feedback back into the conversation
                    conversation.append({"role": "user", "content": user_response})
                    continue

                break

            # Check for a question
            q_match = re.search(r"QUESTION:\s*(.+?)(?:\n|$)", response_text)
            if q_match:
                question_text = q_match.group(1).strip()
                preamble = re.split(r"\n*QUESTION:", response_text)[0].strip()
                if preamble:
                    await _write_log(run_id, "text", preamble)
                await _write_log(run_id, "question", question_text)

                last_id = await _get_current_max_log_id(run_id)
                user_response = await _wait_for_user_prompt(run_id, last_id)
                if user_response is None:
                    await _write_log(run_id, "status", "Timed out waiting for user response — finalizing with current info")
                    result.updated_description = issue_description
                    break

                conversation.append({"role": "user", "content": user_response})
            else:
                # No protocol marker — treat as implicit finalization
                if response_text.strip():
                    await _write_log(run_id, "text", response_text.strip())
                await _write_log(run_id, "status", "Agent completed without explicit finalization marker")
                result.updated_description = response_text.strip() or issue_description
                break

    except Exception as exc:
        logger.exception("Requirements agent error for run %d", run_id)
        result.status = "failed"
        result.error = str(exc)
        await _write_log(run_id, "error", f"Requirements agent error: {exc}")

    return result
