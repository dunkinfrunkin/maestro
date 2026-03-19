"""Pipeline dispatcher — triggers agents when task status changes."""

from __future__ import annotations

import asyncio
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from maestro.db import crud
from maestro.db.engine import get_session
from maestro.db.models import (
    AgentRun,
    AgentRunStatus,
    AgentType,
    ApiKeyProvider,
    PipelineStatus,
    TaskPipelineRecord,
)
from maestro.agent.plugin import registry

logger = logging.getLogger(__name__)

# Map pipeline status → agent type
STATUS_TO_AGENT: dict[str, str] = {
    PipelineStatus.IMPLEMENT.value: AgentType.IMPLEMENTATION.value,
    PipelineStatus.REVIEW.value: AgentType.REVIEW.value,
    PipelineStatus.RISK_PROFILE.value: AgentType.RISK_PROFILE.value,
    PipelineStatus.DEPLOY.value: AgentType.DEPLOYMENT.value,
    PipelineStatus.MONITOR.value: AgentType.MONITOR.value,
}


async def dispatch_agent_for_status(
    workspace_id: int,
    task_pipeline_id: int,
    status: str,
    issue_title: str = "",
    issue_description: str = "",
    issue_url: str = "",
) -> int | None:
    """Dispatch the appropriate agent for a pipeline status change.

    Returns the agent_run ID if dispatched, None if skipped.
    """
    agent_name = STATUS_TO_AGENT.get(status)
    if not agent_name:
        return None

    plugin = registry.get(agent_name)
    if not plugin:
        logger.warning("No plugin registered for agent: %s", agent_name)
        return None

    # Check if agent is enabled
    async with get_session() as session:
        agent_config = await crud.get_agent_config(
            session, workspace_id, AgentType(agent_name)
        )
        if agent_config:
            try:
                extra = json.loads(agent_config.extra_config) if agent_config.extra_config else {}
            except (json.JSONDecodeError, TypeError):
                extra = {}
            if not extra.get("enabled", True):
                logger.info("Agent %s is disabled, skipping", agent_name)
                return None

        # Check API key
        api_key_record = await crud.get_api_key(session, workspace_id, ApiKeyProvider.ANTHROPIC)
        if not api_key_record:
            logger.warning("No Anthropic API key for workspace %d, skipping agent", workspace_id)
            return None
        from maestro.db.encryption import decrypt_token
        api_key = decrypt_token(api_key_record.encrypted_key)

        # Get task pipeline record for PR info
        task_record = await session.get(TaskPipelineRecord, task_pipeline_id)
        pr_url = task_record.pr_url if task_record else ""
        pr_number = task_record.pr_number if task_record else ""
        repo = task_record.repo if task_record else ""

        model = agent_config.model if agent_config else "claude-sonnet-4-6"

        # Create agent run record
        run = AgentRun(
            workspace_id=workspace_id,
            task_pipeline_id=task_pipeline_id,
            agent_type=AgentType(agent_name),
            status=AgentRunStatus.PENDING,
            model=model,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    # Dispatch in background
    asyncio.create_task(
        _execute_agent(
            run_id=run_id,
            plugin=plugin,
            api_key=api_key,
            model=model,
            workspace_id=workspace_id,
            task_pipeline_id=task_pipeline_id,
            issue_title=issue_title,
            issue_description=issue_description,
            issue_url=issue_url,
            pr_url=pr_url,
            pr_number=pr_number,
            repo=repo,
            extra_config=extra if agent_config else {},
        )
    )

    return run_id


async def _execute_agent(
    run_id: int,
    plugin,
    api_key: str,
    model: str,
    workspace_id: int,
    task_pipeline_id: int,
    issue_title: str,
    issue_description: str,
    issue_url: str,
    pr_url: str,
    pr_number: str,
    repo: str,
    extra_config: dict,
) -> None:
    """Execute an agent in the background."""
    # Mark as running
    async with get_session() as session:
        run = await session.get(AgentRun, run_id)
        if run:
            run.status = AgentRunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

    # Create workspace directory
    workspace_path = tempfile.mkdtemp(prefix=f"maestro-agent-{run_id}-")

    # If we have a repo, clone it
    if repo:
        proc = await asyncio.create_subprocess_shell(
            f"git clone https://github.com/{repo}.git {workspace_path}/repo",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        if proc.returncode == 0:
            workspace_path = f"{workspace_path}/repo"

    try:
        context = {
            "api_key": api_key,
            "model": model,
            "workspace_path": workspace_path,
            "issue_title": issue_title,
            "issue_description": issue_description,
            "issue_url": issue_url,
            "pr_url": pr_url,
            "pr_number": pr_number,
            "repo": repo,
            "repo_url": f"https://github.com/{repo}" if repo else "",
            "deployment_ref": pr_number or issue_title,
            "extra_config": extra_config,
        }

        result = await plugin.run(context)

        # Update run record
        async with get_session() as session:
            run = await session.get(AgentRun, run_id)
            if run:
                run.status = (
                    AgentRunStatus.COMPLETED
                    if result.status == "completed"
                    else AgentRunStatus.FAILED
                )
                run.summary = result.summary or ""
                run.error = result.error or ""
                run.cost_usd = result.total_cost_usd
                run.finished_at = datetime.now(timezone.utc)
                await session.commit()

            # If implementation agent completed, try to extract PR URL from result
            if (
                plugin.name == "implementation"
                and result.status == "completed"
                and result.data.get("pr_url")
            ):
                task = await session.get(TaskPipelineRecord, task_pipeline_id)
                if task:
                    task.pr_url = result.data["pr_url"]
                    task.pr_number = result.data.get("pr_number", "")
                    await session.commit()

        logger.info(
            "Agent run %d (%s) finished: %s",
            run_id,
            plugin.name,
            result.status,
        )

    except Exception as exc:
        logger.exception("Agent run %d failed", run_id)
        async with get_session() as session:
            run = await session.get(AgentRun, run_id)
            if run:
                run.status = AgentRunStatus.FAILED
                run.error = str(exc)
                run.finished_at = datetime.now(timezone.utc)
                await session.commit()
