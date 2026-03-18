"""Tests for workspace manager."""

from __future__ import annotations

import pytest

from maestro.workspace.manager import WorkspaceManager, sanitize_identifier


def test_sanitize_identifier():
    assert sanitize_identifier("PROJ-123") == "PROJ-123"
    assert sanitize_identifier("PROJ 123") == "PROJ_123"
    assert sanitize_identifier("a/b\\c:d") == "a_b_c_d"
    assert sanitize_identifier("hello_world.v2") == "hello_world.v2"


@pytest.mark.asyncio
async def test_ensure_workspace_creates_dir(tmp_path):
    mgr = WorkspaceManager(root=tmp_path)
    result = await mgr.ensure_workspace("PROJ-1")
    assert result.created_now is True
    assert result.path.exists()
    assert result.path.name == "PROJ-1"
    assert str(result.path).startswith(str(tmp_path))


@pytest.mark.asyncio
async def test_ensure_workspace_reuses_existing(tmp_path):
    mgr = WorkspaceManager(root=tmp_path)
    r1 = await mgr.ensure_workspace("PROJ-1")
    r2 = await mgr.ensure_workspace("PROJ-1")
    assert r1.path == r2.path
    assert r1.created_now is True
    assert r2.created_now is False


@pytest.mark.asyncio
async def test_ensure_workspace_sanitizes(tmp_path):
    mgr = WorkspaceManager(root=tmp_path)
    result = await mgr.ensure_workspace("feat/bad name")
    assert result.path.name == "feat_bad_name"
    assert result.path.exists()


@pytest.mark.asyncio
async def test_remove_workspace(tmp_path):
    mgr = WorkspaceManager(root=tmp_path)
    await mgr.ensure_workspace("PROJ-2")
    ws_dir = tmp_path / "PROJ-2"
    assert ws_dir.exists()
    await mgr.remove_workspace("PROJ-2")
    assert not ws_dir.exists()


@pytest.mark.asyncio
async def test_after_create_hook_success(tmp_path):
    mgr = WorkspaceManager(
        root=tmp_path,
        hooks={"after_create": "touch .initialized"},
    )
    result = await mgr.ensure_workspace("PROJ-3")
    assert (result.path / ".initialized").exists()


@pytest.mark.asyncio
async def test_after_create_hook_failure_aborts(tmp_path):
    mgr = WorkspaceManager(
        root=tmp_path,
        hooks={"after_create": "exit 1"},
    )
    with pytest.raises(RuntimeError, match="after_create hook failed"):
        await mgr.ensure_workspace("PROJ-4")
    # Workspace should be cleaned up
    assert not (tmp_path / "PROJ-4").exists()


@pytest.mark.asyncio
async def test_before_run_hook(tmp_path):
    mgr = WorkspaceManager(
        root=tmp_path,
        hooks={"before_run": "echo ok"},
    )
    result = await mgr.ensure_workspace("PROJ-5")
    assert await mgr.run_before_run(result.path) is True


@pytest.mark.asyncio
async def test_before_run_hook_failure(tmp_path):
    mgr = WorkspaceManager(
        root=tmp_path,
        hooks={"before_run": "exit 1"},
    )
    result = await mgr.ensure_workspace("PROJ-6")
    assert await mgr.run_before_run(result.path) is False
