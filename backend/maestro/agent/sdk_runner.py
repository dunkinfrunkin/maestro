"""SDK runner — executes Claude Agent SDK with real-time log streaming to DB."""

from __future__ import annotations

import logging
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, query, AssistantMessage, ResultMessage

from maestro.db.engine import get_session
from maestro.db.models import AgentRunLog

logger = logging.getLogger(__name__)


async def _write_log(run_id: int, entry_type: str, content: str) -> None:
    """Write a log entry to the database."""
    try:
        async with get_session() as session:
            log = AgentRunLog(
                agent_run_id=run_id,
                entry_type=entry_type,
                content=content[:2000],  # cap at 2000 chars
            )
            session.add(log)
            await session.commit()
    except Exception:
        logger.exception("Failed to write agent log entry")


async def run_sdk_with_logging(
    run_id: int,
    system_prompt: str,
    prompt: str,
    model: str,
    workspace_path: str,
    allowed_tools: list[str],
) -> dict[str, Any]:
    """Run the Claude Agent SDK and stream log entries to the DB.

    Returns dict with: status, summary, error, total_cost_usd, messages
    """
    messages: list[dict[str, Any]] = []
    status = "completed"
    error = None
    total_cost_usd = 0.0
    last_text = ""

    await _write_log(run_id, "status", "Agent starting...")

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                model=model,
                system_prompt=system_prompt,
                allowed_tools=allowed_tools,
                cwd=workspace_path,
            ),
        ):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if hasattr(block, "name"):
                        tool_name = block.name
                        # Get a useful snippet of what the tool is doing
                        tool_input = ""
                        if hasattr(block, "input") and isinstance(block.input, dict):
                            if "command" in block.input:
                                tool_input = str(block.input["command"])[:200]
                            elif "file_path" in block.input:
                                tool_input = str(block.input["file_path"])
                            elif "pattern" in block.input:
                                tool_input = str(block.input["pattern"])

                        log_content = f"Using tool: {tool_name}"
                        if tool_input:
                            log_content += f" — {tool_input}"

                        await _write_log(run_id, "tool_use", log_content)
                        messages.append({"type": "tool_use", "tool": tool_name})

                    elif hasattr(block, "text") and block.text:
                        text = block.text.strip()
                        if text:
                            last_text = text
                            # Log text in chunks if long
                            if len(text) > 300:
                                await _write_log(run_id, "text", text[:300] + "...")
                            else:
                                await _write_log(run_id, "text", text)
                            messages.append({"type": "text", "text": text[:500]})

            elif isinstance(message, ResultMessage):
                total_cost_usd = getattr(message, "total_cost_usd", 0.0) or 0.0
                if message.subtype == "success":
                    status = "completed"
                    await _write_log(run_id, "status", "Agent completed successfully")
                else:
                    status = "failed"
                    error = message.subtype
                    await _write_log(run_id, "error", f"Agent failed: {message.subtype}")

    except Exception as exc:
        status = "failed"
        error = str(exc)
        await _write_log(run_id, "error", f"Agent error: {exc}")
        logger.exception("SDK runner failed for run %d", run_id)

    return {
        "status": status,
        "error": error,
        "total_cost_usd": total_cost_usd,
        "messages": messages,
        "last_text": last_text,
    }
