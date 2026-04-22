"""Orchestrator engine — polling, dispatch, reconciliation, retry."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from maestro.agents.prompt import render_prompt
from maestro.agents.runner import AgentRunner, TurnResult
from maestro.config.loader import ConfigLoader
from maestro.config.schema import ServiceConfig
from maestro.models import Issue, RetryEntry, RunAttempt, RunAttemptStatus
from maestro.orchestrator.state import RuntimeState
from maestro.tracker.base import TrackerClient
from maestro.workspace.manager import WorkspaceManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """Core orchestration loop per the Symphony specification.

    Lifecycle:
    1. Startup terminal cleanup
    2. Poll tick loop:
       a. Reconcile running issues
       b. Validate dispatch config
       c. Fetch candidate issues
       d. Sort by priority, creation time, identifier
       e. Dispatch while slots available
    """

    def __init__(
        self,
        config_loader: ConfigLoader,
        tracker: TrackerClient | None = None,
    ) -> None:
        self._loader = config_loader
        self._tracker = tracker
        self._state = RuntimeState()
        self._workspace_mgr: WorkspaceManager | None = None
        self._agent_runner: AgentRunner | None = None
        self._poll_task: asyncio.Task[None] | None = None
        self._worker_tasks: dict[str, asyncio.Task[None]] = {}
        self._refresh_event = asyncio.Event()

    @property
    def state(self) -> RuntimeState:
        return self._state

    @property
    def config(self) -> ServiceConfig:
        return self._loader.config

    def _build_components(self) -> None:
        """(Re)build workspace manager and agent runner from current config."""
        cfg = self.config
        self._workspace_mgr = WorkspaceManager(
            root=cfg.workspace.root,
            hooks={
                "after_create": cfg.hooks.after_create,
                "before_run": cfg.hooks.before_run,
                "after_run": cfg.hooks.after_run,
                "before_remove": cfg.hooks.before_remove,
            },
            hook_timeout_ms=cfg.hooks.timeout_ms,
        )
        self._agent_runner = AgentRunner(
            command=cfg.codex.command,
            read_timeout_ms=cfg.codex.read_timeout_ms,
            turn_timeout_ms=cfg.codex.turn_timeout_ms,
            stall_timeout_ms=cfg.codex.stall_timeout_ms,
        )

    async def start(self) -> None:
        """Start the orchestrator: cleanup, then begin polling."""
        self._loader.load()
        self._build_components()
        self._loader.on_change(self._on_config_change)

        await self._startup_cleanup()
        self._poll_task = asyncio.create_task(self._poll_loop())
        await self._loader.start_watching()
        logger.info("Orchestrator started")

    async def stop(self) -> None:
        """Gracefully stop the orchestrator."""
        await self._loader.stop_watching()
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass

        # Cancel all worker tasks
        for task in self._worker_tasks.values():
            task.cancel()
        if self._worker_tasks:
            await asyncio.gather(*self._worker_tasks.values(), return_exceptions=True)

        logger.info("Orchestrator stopped")

    def trigger_refresh(self) -> None:
        """Queue an immediate poll/reconciliation cycle."""
        self._refresh_event.set()

    def _on_config_change(self, cfg: ServiceConfig) -> None:
        logger.info("Config changed, rebuilding components")
        self._build_components()

    # -----------------------------------------------------------------------
    # Startup
    # -----------------------------------------------------------------------

    async def _startup_cleanup(self) -> None:
        """Query terminal-state issues and remove corresponding workspaces."""
        if not self._tracker:
            return
        cfg = self.config
        try:
            terminal_issues = await self._tracker.fetch_issues_by_states(cfg.tracker.terminal_states)
            for issue in terminal_issues:
                assert self._workspace_mgr is not None
                await self._workspace_mgr.remove_workspace(issue.identifier)
            logger.info("Startup cleanup: removed %d terminal workspaces", len(terminal_issues))
        except Exception:
            logger.exception("Startup cleanup failed")

    # -----------------------------------------------------------------------
    # Poll loop
    # -----------------------------------------------------------------------

    async def _poll_loop(self) -> None:
        """Main polling loop."""
        while True:
            try:
                await self._poll_tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Poll tick error")

            # Wait for interval or refresh trigger
            cfg = self.config
            interval = cfg.polling.interval_ms / 1000.0
            try:
                await asyncio.wait_for(self._refresh_event.wait(), timeout=interval)
                self._refresh_event.clear()
            except asyncio.TimeoutError:
                pass

    async def _poll_tick(self) -> None:
        """Single poll tick per the spec sequence."""
        # Step 1: Reconcile running issues
        await self._reconcile()

        # Step 2: Process retry queue
        await self._process_retries()

        # Step 3: Validate dispatch config
        if not self._validate_dispatch():
            return

        # Step 4: Fetch candidates
        try:
            candidates = await self._tracker.fetch_candidate_issues()
        except Exception:
            logger.exception("Failed to fetch candidates — skipping tick")
            return

        # Step 5: Sort by priority, creation time, identifier
        candidates.sort(key=_issue_sort_key)

        # Step 6: Dispatch while slots available
        cfg = self.config
        for issue in candidates:
            if self._state.available_slots(cfg.agent.max_concurrent_agents) <= 0:
                break
            if self._is_eligible(issue, cfg):
                await self._dispatch(issue)

    def _validate_dispatch(self) -> bool:
        """Preflight validation before dispatching."""
        if not self._tracker:
            return False
        cfg = self.config
        if not cfg.tracker.api_key:
            return False
        if not cfg.tracker.project_slug:
            return False
        return True

    def _is_eligible(self, issue: Issue, cfg: ServiceConfig) -> bool:
        """Check if an issue is eligible for dispatch."""
        # Already running or claimed
        if issue.id in self._state.running or issue.id in self._state.claimed:
            return False

        # State checks
        if issue.state not in cfg.tracker.active_states:
            return False
        if issue.state in cfg.tracker.terminal_states:
            return False

        # Per-state concurrency
        by_state = cfg.agent.max_concurrent_agents_by_state
        if issue.state in by_state:
            current = sum(
                1
                for a in self._state.running.values()
                if a.issue_identifier  # proxy for state tracking
            )
            # Simplified: count running in this state
            # In production, track state per running issue

        # Todo blockers: all blockers must be in terminal states
        # (would need additional state tracking for full implementation)
        if issue.state == "Todo" and issue.blocked_by:
            # For now, skip blocked issues
            return False

        return True

    # -----------------------------------------------------------------------
    # Dispatch & Worker
    # -----------------------------------------------------------------------

    async def _dispatch(self, issue: Issue) -> None:
        """Dispatch a worker for an issue."""
        if not self._state.claim(issue.id):
            return

        logger.info("Dispatching worker for %s: %s", issue.identifier, issue.title)

        attempt = RunAttempt(
            issue_id=issue.id,
            issue_identifier=issue.identifier,
            workspace_path="",
            started_at=datetime.now(timezone.utc),
        )
        self._state.add_running(issue.id, attempt)

        task = asyncio.create_task(self._worker(issue, attempt))
        self._worker_tasks[issue.id] = task
        task.add_done_callback(lambda t: self._worker_tasks.pop(issue.id, None))

    async def _worker(self, issue: Issue, attempt: RunAttempt) -> None:
        """Worker attempt lifecycle per the spec."""
        assert self._workspace_mgr is not None
        assert self._agent_runner is not None

        try:
            # Step 1: Prepare workspace
            attempt.status = RunAttemptStatus.PREPARING_WORKSPACE
            ws = await self._workspace_mgr.ensure_workspace(issue.identifier)
            attempt.workspace_path = str(ws.path)

            # Step 2: Run before_run hook
            if not await self._workspace_mgr.run_before_run(ws.path):
                attempt.status = RunAttemptStatus.FAILED
                attempt.error = "before_run hook failed"
                self._on_worker_exit(issue, attempt, failed=True)
                return

            # Step 3: Build prompt
            attempt.status = RunAttemptStatus.BUILDING_PROMPT
            wf = self._loader.workflow
            try:
                issue_dict = issue.model_dump(mode="json")
                retry_num = attempt.attempt_number if attempt.attempt_number > 1 else None
                prompt = render_prompt(wf.prompt_template, issue_dict, attempt=retry_num)
            except Exception as exc:
                attempt.status = RunAttemptStatus.FAILED
                attempt.error = f"Prompt render failed: {exc}"
                self._on_worker_exit(issue, attempt, failed=True)
                return

            # Step 4: Run agent turn(s)
            attempt.status = RunAttemptStatus.LAUNCHING_AGENT
            thread_id: str | None = None
            max_turns = 10  # Reasonable default

            for turn_num in range(max_turns):
                attempt.status = RunAttemptStatus.STREAMING_TURN
                outcome = await self._agent_runner.run_turn(
                    workspace=ws.path,
                    prompt=prompt if turn_num == 0 else "Continue.",
                    thread_id=thread_id,
                )

                thread_id = outcome.session.thread_id or thread_id

                # Accumulate token metrics
                self._state.codex_totals.total_input_tokens += outcome.session.input_tokens
                self._state.codex_totals.total_output_tokens += outcome.session.output_tokens

                if outcome.result == TurnResult.COMPLETED:
                    attempt.status = RunAttemptStatus.SUCCEEDED
                    break
                elif outcome.result in (
                    TurnResult.FAILED,
                    TurnResult.CANCELLED,
                    TurnResult.TIMED_OUT,
                    TurnResult.STALLED,
                ):
                    attempt.status = RunAttemptStatus.FAILED
                    attempt.error = outcome.error
                    break
                elif outcome.result == TurnResult.PROCESS_EXIT:
                    # Normal exit without completion — may continue
                    break

            # Step 5: Run after_run hook
            attempt.finished_at = datetime.now(timezone.utc)
            await self._workspace_mgr.run_after_run(ws.path)

            failed = attempt.status != RunAttemptStatus.SUCCEEDED
            self._on_worker_exit(issue, attempt, failed=failed)

        except asyncio.CancelledError:
            attempt.status = RunAttemptStatus.CANCELED
            self._state.remove_running(issue.id)
            self._state.release(issue.id)
            raise
        except Exception as exc:
            logger.exception("Worker error for %s", issue.identifier)
            attempt.status = RunAttemptStatus.FAILED
            attempt.error = str(exc)
            self._on_worker_exit(issue, attempt, failed=True)

    def _on_worker_exit(self, issue: Issue, attempt: RunAttempt, failed: bool) -> None:
        """Handle worker completion: schedule retry or release."""
        removed = self._state.remove_running(issue.id)

        if removed:
            elapsed = 0.0
            if attempt.started_at and attempt.finished_at:
                elapsed = (attempt.finished_at - attempt.started_at).total_seconds()
            self._state.codex_totals.total_seconds_running += elapsed

        if failed:
            # Schedule exponential backoff retry
            cfg = self.config
            backoff_ms = min(
                10000 * (2 ** (attempt.attempt_number - 1)),
                cfg.agent.max_retry_backoff_ms,
            )
            retry_time = datetime.now(timezone.utc)
            entry = RetryEntry(
                issue_id=issue.id,
                issue_identifier=issue.identifier,
                attempt_number=attempt.attempt_number + 1,
                scheduled_at=retry_time,
                backoff_ms=backoff_ms,
            )
            self._state.schedule_retry(entry)
            logger.info(
                "Scheduled retry #%d for %s in %dms",
                entry.attempt_number,
                issue.identifier,
                backoff_ms,
            )
        else:
            # Success — release claim
            self._state.release(issue.id)
            logger.info("Worker succeeded for %s", issue.identifier)

    # -----------------------------------------------------------------------
    # Reconciliation
    # -----------------------------------------------------------------------

    async def _reconcile(self) -> None:
        """Reconcile running issues: stall detection + state refresh."""
        if not self._tracker or not self._state.running:
            return

        cfg = self.config
        issue_ids = list(self._state.running.keys())

        try:
            current_states = await self._tracker.fetch_issue_states_by_ids(issue_ids)
        except Exception:
            logger.exception("Reconciliation state refresh failed — keeping workers")
            return

        for issue_id in issue_ids:
            current_state = current_states.get(issue_id)
            if current_state is None:
                # Issue not found — release
                logger.info("Reconciliation: releasing %s (not found)", issue_id)
                self._state.release(issue_id)
                if issue_id in self._worker_tasks:
                    self._worker_tasks[issue_id].cancel()
            elif current_state in cfg.tracker.terminal_states:
                # Terminal — cleanup
                logger.info("Reconciliation: %s reached terminal state %s", issue_id, current_state)
                self._state.release(issue_id)
                if issue_id in self._worker_tasks:
                    self._worker_tasks[issue_id].cancel()
                attempt = self._state.running.get(issue_id)
                if attempt and self._workspace_mgr:
                    await self._workspace_mgr.remove_workspace(attempt.issue_identifier)
            elif current_state in cfg.tracker.active_states:
                # Still active — keep running
                pass
            else:
                # Neither terminal nor active — release
                logger.info("Reconciliation: releasing %s (state: %s)", issue_id, current_state)
                self._state.release(issue_id)
                if issue_id in self._worker_tasks:
                    self._worker_tasks[issue_id].cancel()

    async def _process_retries(self) -> None:
        """Check retry queue and re-dispatch eligible entries."""
        now = time.time()
        cfg = self.config

        for issue_id, entry in list(self._state.retry_queue.items()):
            elapsed_ms = (now - entry.scheduled_at.timestamp()) * 1000
            if elapsed_ms < entry.backoff_ms:
                continue

            # Check if we have slots
            if self._state.available_slots(cfg.agent.max_concurrent_agents) <= 0:
                break

            # Fetch current state to verify still active
            try:
                states = await self._tracker.fetch_issue_states_by_ids([issue_id])
                current_state = states.get(issue_id)
                if not current_state or current_state not in cfg.tracker.active_states:
                    # No longer active — release
                    self._state.release(issue_id)
                    continue
            except Exception:
                logger.exception("Retry state check failed for %s", issue_id)
                continue

            # Re-dispatch
            self._state.retry_queue.pop(issue_id, None)
            issue = Issue(
                id=issue_id,
                identifier=entry.issue_identifier,
                title="",
                state=current_state,
            )
            attempt = RunAttempt(
                issue_id=issue_id,
                issue_identifier=entry.issue_identifier,
                workspace_path="",
                attempt_number=entry.attempt_number,
                started_at=datetime.now(timezone.utc),
            )
            self._state.add_running(issue_id, attempt)
            task = asyncio.create_task(self._worker(issue, attempt))
            self._worker_tasks[issue_id] = task
            task.add_done_callback(lambda t: self._worker_tasks.pop(issue_id, None))


def _issue_sort_key(issue: Issue) -> tuple:
    """Sort issues by priority (ascending, nulls last), created_at, identifier."""
    priority = issue.priority if issue.priority is not None else 999
    created = issue.created_at or datetime.min.replace(tzinfo=timezone.utc)
    return (priority, created, issue.identifier)
