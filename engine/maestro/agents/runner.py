"""Agent runner — subprocess management with line-delimited JSON protocol."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TurnResult(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    STALLED = "stalled"
    PROCESS_EXIT = "process_exit"


@dataclass
class SessionMetrics:
    session_id: str = ""
    thread_id: str = ""
    turn_count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    started_at: float = 0.0
    last_event_at: float = 0.0


@dataclass
class TurnOutcome:
    result: TurnResult
    session: SessionMetrics
    error: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)


class AgentRunner:
    """Manages agent subprocess lifecycle per the Symphony spec.

    Launches the agent command via `bash -lc <command>`, communicates
    via line-delimited JSON on stdout, handles startup handshake,
    turn processing, and timeouts.
    """

    def __init__(
        self,
        command: str,
        read_timeout_ms: int = 5000,
        turn_timeout_ms: int = 3600000,
        stall_timeout_ms: int = 300000,
    ) -> None:
        self._command = command
        self._read_timeout = read_timeout_ms / 1000.0
        self._turn_timeout = turn_timeout_ms / 1000.0
        self._stall_timeout = stall_timeout_ms / 1000.0 if stall_timeout_ms > 0 else None

    async def run_turn(
        self,
        workspace: Path,
        prompt: str,
        thread_id: str | None = None,
    ) -> TurnOutcome:
        """Launch agent subprocess, run a single turn, return outcome.

        For continuation runs, pass an existing thread_id.
        """
        session = SessionMetrics(started_at=time.time())
        events: list[dict[str, Any]] = []

        try:
            proc = await asyncio.create_subprocess_shell(
                f"bash -lc {_shell_quote(self._command)}",
                cwd=str(workspace),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as exc:
            return TurnOutcome(
                result=TurnResult.FAILED,
                session=session,
                error=f"Failed to launch agent: {exc}",
            )

        try:
            # --- Startup handshake ---
            # Send initialize request
            init_req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"prompt": prompt},
            }
            if thread_id:
                init_req["params"]["thread_id"] = thread_id  # type: ignore[index]

            await self._send(proc, init_req)

            # Read initialize response
            init_resp = await self._read_message(proc, self._read_timeout)
            if init_resp is None:
                return TurnOutcome(
                    result=TurnResult.FAILED,
                    session=session,
                    error="No initialize response from agent",
                )
            events.append(init_resp)

            # Extract thread_id from response
            if "result" in init_resp:
                session.thread_id = init_resp["result"].get("thread_id", "")

            # --- Turn processing ---
            turn_start = time.time()
            turn_deadline = turn_start + self._turn_timeout

            while True:
                now = time.time()
                if now >= turn_deadline:
                    await self._kill(proc)
                    return TurnOutcome(
                        result=TurnResult.TIMED_OUT,
                        session=session,
                        error="Turn timeout exceeded",
                        events=events,
                    )

                # Stall timeout: time since last event
                read_limit = turn_deadline - now
                if self._stall_timeout is not None:
                    read_limit = min(read_limit, self._stall_timeout)

                msg = await self._read_message(proc, read_limit)

                if msg is None:
                    # Check if process exited
                    if proc.returncode is not None:
                        return TurnOutcome(
                            result=TurnResult.PROCESS_EXIT,
                            session=session,
                            error=f"Agent process exited with code {proc.returncode}",
                            events=events,
                        )
                    # Stall
                    if self._stall_timeout is not None:
                        await self._kill(proc)
                        return TurnOutcome(
                            result=TurnResult.STALLED,
                            session=session,
                            error="Agent stalled (no activity)",
                            events=events,
                        )
                    continue

                events.append(msg)
                session.last_event_at = time.time()
                session.turn_count += 1

                # Track token usage from events
                if "usage" in msg.get("params", {}):
                    usage = msg["params"]["usage"]
                    session.input_tokens += usage.get("input_tokens", 0)
                    session.output_tokens += usage.get("output_tokens", 0)

                # Check for turn completion events
                method = msg.get("method", "")
                if method == "turn/completed":
                    return TurnOutcome(
                        result=TurnResult.COMPLETED,
                        session=session,
                        events=events,
                    )
                elif method == "turn/failed":
                    return TurnOutcome(
                        result=TurnResult.FAILED,
                        session=session,
                        error=msg.get("params", {}).get("error", "Turn failed"),
                        events=events,
                    )
                elif method == "turn/cancelled":
                    return TurnOutcome(
                        result=TurnResult.CANCELLED,
                        session=session,
                        error="Turn cancelled",
                        events=events,
                    )
                elif method == "turn/input_required":
                    # Spec: user-input requests trigger hard failure
                    await self._kill(proc)
                    return TurnOutcome(
                        result=TurnResult.FAILED,
                        session=session,
                        error="Agent requested user input (not supported)",
                        events=events,
                    )

        except asyncio.CancelledError:
            await self._kill(proc)
            raise
        except Exception as exc:
            await self._kill(proc)
            return TurnOutcome(
                result=TurnResult.FAILED,
                session=session,
                error=f"Agent runner error: {exc}",
                events=events,
            )

    async def _send(self, proc: asyncio.subprocess.Process, msg: dict[str, Any]) -> None:
        assert proc.stdin is not None
        line = json.dumps(msg) + "\n"
        proc.stdin.write(line.encode())
        await proc.stdin.drain()

    async def _read_message(
        self, proc: asyncio.subprocess.Process, timeout: float
    ) -> dict[str, Any] | None:
        assert proc.stdout is not None
        try:
            line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
            if not line:
                return None
            return json.loads(line.decode().strip())
        except asyncio.TimeoutError:
            return None
        except json.JSONDecodeError as exc:
            logger.warning("Malformed JSON from agent: %s", exc)
            return {"method": "malformed", "params": {"error": str(exc)}}

    async def _kill(self, proc: asyncio.subprocess.Process) -> None:
        try:
            proc.kill()
            await proc.wait()
        except ProcessLookupError:
            pass


def _shell_quote(s: str) -> str:
    """Quote a string for safe shell usage."""
    return "'" + s.replace("'", "'\\''") + "'"
