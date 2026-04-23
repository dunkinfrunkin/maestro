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
                content=content,
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
    import re
    messages: list[dict[str, Any]] = []
    status = "completed"
    error = None
    total_cost_usd = 0.0
    last_text = ""
    all_text = ""  # accumulate all text for keyword detection
    review_verdict = ""
    pr_url = ""
    _pr_pattern = re.compile(r"https://github\.com/[^\s]+/pull/\d+")

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
                                tool_input = str(block.input["command"])
                            elif "file_path" in block.input:
                                tool_input = str(block.input["file_path"])
                            elif "pattern" in block.input:
                                tool_input = str(block.input["pattern"])

                        log_content = f"Using tool: {tool_name}"
                        if tool_input:
                            log_content += f" — {tool_input}"

                        await _write_log(run_id, "tool_use", log_content)
                        messages.append({"type": "tool_use", "tool": tool_name})

                    # Check tool results for PR URLs
                    if hasattr(block, "content") and isinstance(block.content, str):
                        pr_match = _pr_pattern.search(block.content)
                        if pr_match and not pr_url:
                            pr_url = pr_match.group(0)
                            await _write_log(run_id, "status", f"PR created: {pr_url}")

                    elif hasattr(block, "text") and block.text:
                        text = block.text.strip()
                        if text:
                            last_text = text
                            all_text += "\n" + text
                            # Detect review verdict (handle markdown formatting)
                            clean_text = re.sub(r'[*`_~]', '', text)
                            if "REVIEW_VERDICT:" in clean_text:
                                for vline in clean_text.split("\n"):
                                    if "REVIEW_VERDICT:" in vline:
                                        review_verdict = vline.split("REVIEW_VERDICT:", 1)[1].strip().upper()
                                        review_verdict = re.sub(r'[^A-Z_]', '', review_verdict)
                                        await _write_log(run_id, "status", f"Review verdict: {review_verdict}")
                            # Detect PR URLs
                            pr_match = _pr_pattern.search(text)
                            if pr_match and not pr_url:
                                pr_url = pr_match.group(0)
                                await _write_log(run_id, "status", f"PR created: {pr_url}")
                            await _write_log(run_id, "text", text)
                            messages.append({"type": "text", "text": text})

            elif isinstance(message, ResultMessage):
                total_cost_usd = getattr(message, "total_cost_usd", 0.0) or 0.0
                if message.subtype == "success":
                    status = "completed"
                    await _write_log(run_id, "status", "Agent completed successfully")
                else:
                    status = "failed"
                    error = message.subtype
                    await _write_log(run_id, "error", f"Agent failed: {message.subtype}")

        print(f"[MAESTRO-SDK] Run {run_id} async for loop completed. Status: {status}")

    except Exception as exc:
        status = "failed"
        error = str(exc)
        await _write_log(run_id, "error", f"Agent error: {exc}")
        print(f"[MAESTRO-SDK] Run {run_id} EXCEPTION: {exc}")
        import traceback
        traceback.print_exc()

    print(f"[MAESTRO-SDK] Run {run_id} returning: status={status}, pr_url={pr_url}")
    return {
        "status": status,
        "error": error,
        "total_cost_usd": total_cost_usd,
        "messages": messages,
        "last_text": last_text,
        "all_text": all_text,
        "pr_url": pr_url,
        "review_verdict": review_verdict,
    }
