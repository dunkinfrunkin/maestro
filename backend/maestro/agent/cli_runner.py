"""CLI runner — executes CLI agents (Claude, Codex, etc.) as subprocesses with real-time log streaming."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

from maestro.db.engine import get_session
from maestro.db.models import AgentRunLog

logger = logging.getLogger(__name__)

_pr_pattern = re.compile(r"https://(?:github\.com/[^\s\"']+/pull/\d+|[^\s\"']+/-/merge_requests/\d+)")


# ---------------------------------------------------------------------------
# Shared result accumulator — provider parsers mutate this
# ---------------------------------------------------------------------------


@dataclass
class RunResult:
    status: str = "completed"
    error: str | None = None
    total_cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    messages: list[dict[str, Any]] = field(default_factory=list)
    last_text: str = ""
    all_text: str = ""
    pr_url: str = ""
    review_verdict: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "error": self.error,
            "total_cost_usd": self.total_cost_usd,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "messages": self.messages,
            "last_text": self.last_text,
            "all_text": self.all_text,
            "pr_url": self.pr_url,
            "review_verdict": self.review_verdict,
        }


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _detect_pr_url(text: str) -> str | None:
    """Extract first PR/MR URL from text."""
    m = _pr_pattern.search(text)
    return m.group(0) if m else None


def _detect_review_verdict(text: str) -> str | None:
    """Extract REVIEW_VERDICT from text if present."""
    clean = re.sub(r'[*`_~]', '', text)
    if "REVIEW_VERDICT:" not in clean:
        return None
    for line in clean.split("\n"):
        if "REVIEW_VERDICT:" in line:
            verdict = line.split("REVIEW_VERDICT:", 1)[1].strip().upper()
            return re.sub(r'[^A-Z_]', '', verdict)
    return None


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


async def _process_text(run_id: int, text: str, result: RunResult) -> None:
    """Process a text block: log it, detect PRs, detect verdicts."""
    if not text:
        return
    result.last_text = text
    result.all_text += "\n" + text

    pr = _detect_pr_url(text)
    if pr and not result.pr_url:
        result.pr_url = pr
        await _write_log(run_id, "status", f"PR created: {pr}")

    verdict = _detect_review_verdict(text)
    if verdict and not result.review_verdict:
        result.review_verdict = verdict
        await _write_log(run_id, "status", f"Review verdict: {verdict}")

    if len(text) > 300:
        await _write_log(run_id, "text", text[:300] + "...")
    else:
        await _write_log(run_id, "text", text)
    result.messages.append({"type": "text", "text": text[:500]})


# ---------------------------------------------------------------------------
# Claude CLI: command builder + event parser
# ---------------------------------------------------------------------------


def _build_claude_cmd(prompt: str, model: str, tools_str: str, system_prompt: str) -> list[str]:
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
    return cmd


async def _parse_claude_event(run_id: int, event: dict, result: RunResult) -> None:
    """Parse a single Claude stream-json event."""
    event_type = event.get("type", "")

    if event_type == "tool_result":
        tool_name = event.get("tool", "")
        output = event.get("output", "")
        if output and isinstance(output, str):
            truncated = output[:300] + "..." if len(output) > 300 else output
            await _write_log(run_id, "tool_result", f"[{tool_name}] {truncated}")

    elif event_type == "system" and event.get("message"):
        await _write_log(run_id, "status", event["message"][:500])

    elif event_type == "assistant":
        msg = event.get("message", {})
        for block in msg.get("content", []):
            block_type = block.get("type", "")

            if block_type == "tool_use":
                tool_name = block.get("name", "unknown")
                tool_input = block.get("input", {})

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
                result.messages.append({"type": "tool_use", "tool": tool_name})

            elif block_type == "text":
                text = block.get("text", "").strip()
                await _process_text(run_id, text, result)

    elif event_type == "result":
        result.total_cost_usd = event.get("total_cost_usd", 0.0) or 0.0
        usage = event.get("usage", {})
        result.input_tokens = usage.get("input_tokens", 0) or 0
        result.output_tokens = usage.get("output_tokens", 0) or 0
        result_text = event.get("result", "")
        if result_text:
            await _process_text(run_id, result_text, result)

        is_error = event.get("is_error", False)
        if is_error:
            result.status = "failed"
            result.error = result_text[:500] if result_text else "Agent failed"
            await _write_log(run_id, "error", f"Agent failed: {result.error}")
        else:
            result.status = "completed"
            await _write_log(run_id, "status",
                f"Claude Code CLI completed (cost: ${result.total_cost_usd:.4f}, "
                f"tokens: {result.input_tokens}in/{result.output_tokens}out)")


# ---------------------------------------------------------------------------
# Codex CLI: command builder + event parser
# ---------------------------------------------------------------------------


def _build_codex_cmd(prompt: str, model: str, system_prompt: str) -> list[str]:
    cmd = [
        "codex", "exec",
        "--model", model,
        "--dangerously-bypass-approvals-and-sandbox",
        "--json",
        prompt,
    ]
    return cmd


async def _parse_codex_event(run_id: int, event: dict, result: RunResult) -> None:
    """Parse a single Codex JSONL event.

    Codex events use these types:
      thread.started, turn.started, turn.completed, turn.failed,
      item.started, item.updated, item.completed, error
    """
    event_type = event.get("type", "")

    if event_type == "turn.completed":
        usage = event.get("usage", {})
        result.input_tokens += usage.get("input_tokens", 0) or 0
        result.output_tokens += usage.get("output_tokens", 0) or 0
        await _write_log(run_id, "status",
            f"Turn completed (tokens: {result.input_tokens}in/{result.output_tokens}out)")

    elif event_type == "turn.failed":
        err = event.get("error", {})
        err_msg = err.get("message", "Turn failed") if isinstance(err, dict) else str(err)
        result.status = "failed"
        result.error = err_msg[:500]
        await _write_log(run_id, "error", f"Turn failed: {err_msg[:500]}")

    elif event_type == "error":
        err_msg = event.get("message", "Unknown error")
        result.status = "failed"
        result.error = err_msg[:500]
        await _write_log(run_id, "error", f"Error: {err_msg[:500]}")

    elif event_type in ("item.started", "item.updated", "item.completed"):
        item = event.get("item", {})
        item_type = item.get("type", "")

        if item_type == "agent_message":
            text = item.get("text", "").strip()
            if text and event_type == "item.completed":
                await _process_text(run_id, text, result)

        elif item_type == "command_execution":
            cmd_str = item.get("command", "")
            status_val = item.get("status", "")
            if event_type == "item.started" and cmd_str:
                await _write_log(run_id, "tool_use", f"Running command: {cmd_str[:200]}")
                result.messages.append({"type": "tool_use", "tool": "Bash"})
            elif event_type == "item.completed":
                output = item.get("aggregated_output", "")
                exit_code = item.get("exit_code", "")
                if output:
                    truncated = output[:300] + "..." if len(output) > 300 else output
                    await _write_log(run_id, "tool_result", f"[Bash exit={exit_code}] {truncated}")
                # Check command output for PR URLs
                if output:
                    pr = _detect_pr_url(output)
                    if pr and not result.pr_url:
                        result.pr_url = pr
                        await _write_log(run_id, "status", f"PR created: {pr}")

        elif item_type == "file_change":
            changes = item.get("changes", [])
            if event_type == "item.started" and changes:
                paths = [c.get("path", "") for c in changes[:5]]
                await _write_log(run_id, "tool_use", f"File changes: {', '.join(paths)}")
                result.messages.append({"type": "tool_use", "tool": "Edit"})
            elif event_type == "item.completed" and changes:
                for c in changes:
                    kind = c.get("kind", "update")
                    path = c.get("path", "")
                    await _write_log(run_id, "tool_result", f"[{kind}] {path}")

        elif item_type == "mcp_tool_call":
            tool_name = item.get("tool", "unknown")
            if event_type == "item.started":
                await _write_log(run_id, "tool_use", f"MCP tool: {tool_name}")
                result.messages.append({"type": "tool_use", "tool": tool_name})

        elif item_type == "reasoning":
            text = item.get("text", "").strip()
            if text and event_type == "item.completed":
                await _write_log(run_id, "status", f"Reasoning: {text[:300]}")


# ---------------------------------------------------------------------------
# Unified runner
# ---------------------------------------------------------------------------


async def run_cli_with_logging(
    run_id: int,
    system_prompt: str,
    prompt: str,
    provider: str,
    model: str,
    workspace_path: str,
    allowed_tools: list[str],
    api_key: str,
) -> dict[str, Any]:
    """Run CLI agent and stream log entries to the DB.

    Returns dict with: status, error, total_cost_usd, input_tokens, output_tokens,
    messages, last_text, all_text, pr_url, review_verdict
    """
    result = RunResult()
    tools_str = ",".join(allowed_tools)

    # Build command and env based on provider
    is_codex = provider == "openai"
    cli_name = "Codex CLI" if is_codex else "Claude Code CLI"
    await _write_log(run_id, "status", f"Starting {cli_name} (model: {model}, tools: {tools_str})")

    if is_codex:
        cmd = _build_codex_cmd(prompt, model, system_prompt)
        parse_event = _parse_codex_event
    else:
        cmd = _build_claude_cmd(prompt, model, tools_str, system_prompt)
        parse_event = _parse_claude_event

    env = {**os.environ}
    if is_codex:
        env["OPENAI_API_KEY"] = api_key
    else:
        env["ANTHROPIC_API_KEY"] = api_key

    await _write_log(run_id, "status", f"$ {cmd[0]} ... --model {model}")

    try:
        # Codex CLI requires explicit login — env var alone is not sufficient
        if is_codex:
            login_proc = await asyncio.create_subprocess_exec(
                "codex", "login", "--with-api-key",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            await login_proc.communicate(input=api_key.encode())
            print(f"[MAESTRO-CLI] Run {run_id} codex login exit={login_proc.returncode}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=workspace_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            limit=10 * 1024 * 1024,
        )

        print(f"[MAESTRO-CLI] Run {run_id} started, PID={proc.pid}")

        # Stream stdout line by line — JSONL for both Claude and Codex
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                if line:
                    await _write_log(run_id, "text", line[:500])
                continue

            await parse_event(run_id, event, result)

        await proc.wait()
        print(f"[MAESTRO-CLI] Run {run_id} process exited with code {proc.returncode}")

        # If process failed but parser didn't catch it, check stderr
        if proc.returncode != 0 and result.status == "completed":
            stderr_out = await proc.stderr.read()
            err_text = stderr_out.decode("utf-8", errors="replace")[:500]
            if err_text:
                result.status = "failed"
                result.error = err_text
                await _write_log(run_id, "error", f"Process error: {err_text}")

        # If Codex completed without explicit turn.completed, mark success
        if is_codex and result.status == "completed" and proc.returncode == 0:
            await _write_log(run_id, "status",
                f"Codex CLI completed (tokens: {result.input_tokens}in/{result.output_tokens}out)")

    except Exception as exc:
        result.status = "failed"
        result.error = str(exc)
        await _write_log(run_id, "error", f"Agent error: {exc}")
        print(f"[MAESTRO-CLI] Run {run_id} EXCEPTION: {exc}")
        import traceback
        traceback.print_exc()

    print(f"[MAESTRO-CLI] Run {run_id} returning: status={result.status}, pr_url={result.pr_url}")
    return result.to_dict()
