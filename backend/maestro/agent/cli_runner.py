"""CLI runner — executes Claude Code CLI as subprocess with real-time log streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from maestro.db.engine import get_session
from maestro.db.models import AgentRunLog

logger = logging.getLogger(__name__)

_pr_pattern = re.compile(r"https://github\.com/[^\s\"']+/pull/\d+")


async def _write_log(run_id: int, entry_type: str, content: str) -> None:
    """Write a log entry to the database."""
    try:
        async with get_session() as session:
            log = AgentRunLog(
                agent_run_id=run_id,
                entry_type=entry_type,
                content=content[:2000],
            )
            session.add(log)
            await session.commit()
    except Exception:
        logger.exception("Failed to write agent log entry")


async def run_cli_with_logging(
    run_id: int,
    system_prompt: str,
    prompt: str,
    model: str,
    workspace_path: str,
    allowed_tools: list[str],
    api_key: str,
) -> dict[str, Any]:
    """Run Claude Code CLI and stream log entries to the DB.

    Returns dict with: status, error, total_cost_usd, messages, last_text, all_text, pr_url, review_verdict
    """
    messages: list[dict[str, Any]] = []
    status = "completed"
    error = None
    total_cost_usd = 0.0
    last_text = ""
    all_text = ""
    pr_url = ""
    review_verdict = ""

    tools_str = ",".join(allowed_tools)
    await _write_log(run_id, "status", f"Starting Claude Code CLI (model: {model}, tools: {tools_str})")

    cmd = [
        "claude",
        "-p", prompt,
        "--output-format", "stream-json",
        "--model", model,
        "--allowedTools", tools_str,
        "--verbose",
    ]

    if system_prompt:
        cmd.extend(["--system-prompt", system_prompt])

    await _write_log(run_id, "status", f"$ claude -p '...' --model {model} --output-format stream-json")

    env = {
        "ANTHROPIC_API_KEY": api_key,
        "PATH": "/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin:" +
                "/Users/frankchan/.local/bin:/Users/frankchan/.nvm/versions/node/v22.14.0/bin",
        "HOME": "/Users/frankchan",
        "GH_TOKEN": "",  # Will be populated if available
    }

    # Inherit GH_TOKEN from environment if set
    import os
    if os.environ.get("GH_TOKEN"):
        env["GH_TOKEN"] = os.environ["GH_TOKEN"]
    # Also check for gh auth
    env["GITHUB_TOKEN"] = os.environ.get("GITHUB_TOKEN", "")

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "ANTHROPIC_API_KEY": api_key},
        )

        print(f"[MAESTRO-CLI] Run {run_id} started, PID={proc.pid}")

        # Stream stdout line by line
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                # Non-JSON output — log it
                if line:
                    await _write_log(run_id, "text", line[:500])
                continue

            event_type = event.get("type", "")

            # Log tool results (what the tool returned)
            if event_type == "tool_result":
                tool_name = event.get("tool", "")
                output = event.get("output", "")
                if output and isinstance(output, str):
                    truncated = output[:300] + "..." if len(output) > 300 else output
                    await _write_log(run_id, "tool_result", f"[{tool_name}] {truncated}")

            # Log system messages
            if event_type == "system" and event.get("message"):
                await _write_log(run_id, "status", event["message"][:500])

            if event_type == "assistant":
                msg = event.get("message", {})
                for block in msg.get("content", []):
                    block_type = block.get("type", "")

                    if block_type == "tool_use":
                        tool_name = block.get("name", "unknown")
                        tool_input = block.get("input", {})

                        # Get a useful snippet
                        snippet = ""
                        if isinstance(tool_input, dict):
                            if "command" in tool_input:
                                snippet = str(tool_input["command"])[:200]
                            elif "file_path" in tool_input:
                                snippet = str(tool_input["file_path"])
                            elif "pattern" in tool_input:
                                snippet = str(tool_input["pattern"])

                        log_content = f"Using tool: {tool_name}"
                        if snippet:
                            log_content += f" — {snippet}"

                        await _write_log(run_id, "tool_use", log_content)
                        messages.append({"type": "tool_use", "tool": tool_name})

                    elif block_type == "text":
                        text = block.get("text", "").strip()
                        if text:
                            last_text = text
                            all_text += "\n" + text

                            # Detect review verdict
                            clean = re.sub(r'[*`_~]', '', text)
                            if "REVIEW_VERDICT:" in clean:
                                for vline in clean.split("\n"):
                                    if "REVIEW_VERDICT:" in vline:
                                        review_verdict = vline.split("REVIEW_VERDICT:", 1)[1].strip().upper()
                                        review_verdict = re.sub(r'[^A-Z_]', '', review_verdict)
                                        await _write_log(run_id, "status", f"Review verdict: {review_verdict}")

                            # Detect PR URLs
                            pr_match = _pr_pattern.search(text)
                            if pr_match and not pr_url:
                                pr_url = pr_match.group(0)
                                await _write_log(run_id, "status", f"PR created: {pr_url}")

                            # Log text
                            if len(text) > 300:
                                await _write_log(run_id, "text", text[:300] + "...")
                            else:
                                await _write_log(run_id, "text", text)
                            messages.append({"type": "text", "text": text[:500]})

            elif event_type == "result":
                total_cost_usd = event.get("cost_usd", 0.0) or 0.0
                result_text = event.get("result", "")
                if result_text:
                    all_text += "\n" + result_text
                    last_text = result_text

                    # Check result for PR URLs and verdicts
                    pr_match = _pr_pattern.search(result_text)
                    if pr_match and not pr_url:
                        pr_url = pr_match.group(0)

                    clean = re.sub(r'[*`_~]', '', result_text)
                    if "REVIEW_VERDICT:" in clean and not review_verdict:
                        for vline in clean.split("\n"):
                            if "REVIEW_VERDICT:" in vline:
                                review_verdict = vline.split("REVIEW_VERDICT:", 1)[1].strip().upper()
                                review_verdict = re.sub(r'[^A-Z_]', '', review_verdict)

                is_error = event.get("is_error", False)
                if is_error:
                    status = "failed"
                    error = result_text[:500] if result_text else "Agent failed"
                    await _write_log(run_id, "error", f"Agent failed: {error}")
                else:
                    status = "completed"
                    await _write_log(run_id, "status", f"Claude Code CLI completed (cost: ${total_cost_usd:.4f})")

        # Wait for process to exit
        await proc.wait()
        print(f"[MAESTRO-CLI] Run {run_id} process exited with code {proc.returncode}")

        if proc.returncode != 0 and status == "completed":
            stderr_out = await proc.stderr.read()
            err_text = stderr_out.decode("utf-8", errors="replace")[:500]
            if err_text:
                status = "failed"
                error = err_text
                await _write_log(run_id, "error", f"Process error: {err_text}")

    except Exception as exc:
        status = "failed"
        error = str(exc)
        await _write_log(run_id, "error", f"Agent error: {exc}")
        print(f"[MAESTRO-CLI] Run {run_id} EXCEPTION: {exc}")
        import traceback
        traceback.print_exc()

    print(f"[MAESTRO-CLI] Run {run_id} returning: status={status}, pr_url={pr_url}")
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
