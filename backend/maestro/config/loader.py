"""Config loader with file-watching for dynamic reload."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable

from maestro.config.schema import ServiceConfig
from maestro.config.workflow import WorkflowDefinition, build_service_config, parse_workflow

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Loads and optionally watches a WORKFLOW.md for live config updates.

    Keeps the last-known-good config on reload failure (per spec).
    """

    def __init__(
        self,
        workflow_path: str | Path | None = None,
        overrides: dict[str, Any] | None = None,
    ) -> None:
        self._path = Path(workflow_path).resolve() if workflow_path else None
        self._overrides = overrides or {}
        self._workflow: WorkflowDefinition | None = None
        self._config: ServiceConfig | None = None
        self._listeners: list[Callable[[ServiceConfig], Any]] = []
        self._watch_task: asyncio.Task[None] | None = None

    @property
    def workflow(self) -> WorkflowDefinition:
        if self._workflow is None:
            self.load()
        assert self._workflow is not None
        return self._workflow

    @property
    def config(self) -> ServiceConfig:
        if self._config is None:
            self.load()
        assert self._config is not None
        return self._config

    def load(self) -> ServiceConfig:
        """(Re-)parse WORKFLOW.md and build config. Raises on first load failure."""
        if self._path is None:
            self._config = ServiceConfig()
            logger.info("No workflow file — using default config")
            return self._config
        try:
            wf = parse_workflow(self._path)
            cfg = build_service_config(wf, self._overrides)
            self._workflow = wf
            self._config = cfg
            logger.info("Config loaded from %s", self._path)
            return cfg
        except Exception:
            if self._config is not None:
                logger.exception("Config reload failed — keeping last known good config")
                return self._config
            raise

    def on_change(self, callback: Callable[[ServiceConfig], Any]) -> None:
        """Register a listener invoked after successful reload."""
        self._listeners.append(callback)

    async def start_watching(self) -> None:
        """Start a background task that watches WORKFLOW.md for changes."""
        if self._watch_task is not None or self._path is None:
            return
        self._watch_task = asyncio.create_task(self._watch_loop())

    async def stop_watching(self) -> None:
        if self._watch_task is not None:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None

    async def _watch_loop(self) -> None:
        """Poll-based file watcher (simple fallback; can swap for watchfiles later)."""
        last_mtime: float = 0.0
        while True:
            try:
                await asyncio.sleep(2)
                if not self._path.exists():
                    continue
                mtime = self._path.stat().st_mtime
                if mtime != last_mtime:
                    last_mtime = mtime
                    old = self._config
                    self.load()
                    if self._config is not old:
                        for cb in self._listeners:
                            try:
                                cb(self._config)  # type: ignore[arg-type]
                            except Exception:
                                logger.exception("Config change listener error")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Watch loop error")
