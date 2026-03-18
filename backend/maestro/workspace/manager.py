"""Per-issue workspace manager with hook execution and path safety."""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Sanitize: replace anything not alphanumeric, dot, underscore, or hyphen
_SANITIZE_RE = re.compile(r"[^a-zA-Z0-9._-]")


def sanitize_identifier(identifier: str) -> str:
    """Replace non-safe characters with underscores."""
    return _SANITIZE_RE.sub("_", identifier)


@dataclass
class WorkspaceResult:
    path: Path
    created_now: bool


class WorkspaceManager:
    """Manages per-issue filesystem workspaces.

    Safety invariants (per spec):
    1. Agent runs only in per-issue workspace
    2. Workspace path must be inside workspace root
    3. Workspace directory name is sanitized
    """

    def __init__(
        self,
        root: str | Path,
        hooks: dict[str, str | None] | None = None,
        hook_timeout_ms: int = 60000,
    ) -> None:
        self._root = Path(root).resolve()
        self._hooks = hooks or {}
        self._hook_timeout = hook_timeout_ms / 1000.0

    @property
    def root(self) -> Path:
        return self._root

    async def ensure_workspace(self, identifier: str) -> WorkspaceResult:
        """Create or reuse a per-issue workspace directory.

        Returns the path and whether it was freshly created.
        Runs after_create hook on new workspaces.
        """
        safe_name = sanitize_identifier(identifier)
        ws_path = (self._root / safe_name).resolve()

        # Path containment check
        if not str(ws_path).startswith(str(self._root)):
            raise ValueError(
                f"Workspace path {ws_path} escapes root {self._root}"
            )

        created_now = not ws_path.exists()
        if created_now:
            ws_path.mkdir(parents=True, exist_ok=True)
            logger.info("Created workspace %s", ws_path)

            hook = self._hooks.get("after_create")
            if hook:
                ok = await self._run_hook(hook, ws_path, "after_create")
                if not ok:
                    # Spec: after_create failure aborts creation
                    shutil.rmtree(ws_path, ignore_errors=True)
                    raise RuntimeError(
                        f"after_create hook failed for {identifier}"
                    )
        else:
            logger.info("Reusing workspace %s", ws_path)

        return WorkspaceResult(path=ws_path, created_now=created_now)

    async def run_before_run(self, ws_path: Path) -> bool:
        """Run before_run hook. Returns False if hook fails (aborts attempt)."""
        hook = self._hooks.get("before_run")
        if not hook:
            return True
        return await self._run_hook(hook, ws_path, "before_run")

    async def run_after_run(self, ws_path: Path) -> None:
        """Run after_run hook. Failure is logged but ignored."""
        hook = self._hooks.get("after_run")
        if hook:
            await self._run_hook(hook, ws_path, "after_run")

    async def remove_workspace(self, identifier: str) -> None:
        """Remove a workspace directory (e.g., terminal cleanup)."""
        safe_name = sanitize_identifier(identifier)
        ws_path = (self._root / safe_name).resolve()

        if not str(ws_path).startswith(str(self._root)):
            return

        if not ws_path.exists():
            return

        hook = self._hooks.get("before_remove")
        if hook:
            await self._run_hook(hook, ws_path, "before_remove")

        shutil.rmtree(ws_path, ignore_errors=True)
        logger.info("Removed workspace %s", ws_path)

    async def _run_hook(self, command: str, cwd: Path, name: str) -> bool:
        """Execute a hook script in the workspace directory.

        Returns True on success, False on failure.
        """
        logger.info("Running hook %s: %s (cwd=%s)", name, command, cwd)
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self._hook_timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                logger.error("Hook %s timed out after %sms", name, self._hook_timeout * 1000)
                return False

            if proc.returncode != 0:
                logger.error(
                    "Hook %s failed (exit %s): %s",
                    name,
                    proc.returncode,
                    stderr.decode(errors="replace")[:500],
                )
                return False

            logger.info("Hook %s succeeded", name)
            return True

        except Exception:
            logger.exception("Hook %s error", name)
            return False
