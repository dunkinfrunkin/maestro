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

        # If repo is empty, try to get it from the connection or external_ref
        if not repo and task_record:
            conn = await crud.get_connection(session, task_record.tracker_connection_id)
            if conn and conn.project:
                repo = conn.project
            elif task_record.external_ref:
                # external_ref format: "github:conn_id:issue_id"
                # issue identifier might be "owner/repo#number"
                parts = task_record.external_ref.split(":")
                if len(parts) >= 3:
                    issue_id = parts[2]
                    # For issues fetched across all repos, identifier has repo in it
                    # but issue_id here is just the number
                    # Fall back to connection project
                    pass
            # Save repo back to task record for future runs
            if repo:
                task_record.repo = repo
                await session.commit()

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


    # Map agent type to system prompt and tools
AGENT_CONFIGS = {
    "implementation": {
        "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
    },
    "review": {
        "tools": ["Read", "Bash", "Glob", "Grep"],
    },
    "risk_profile": {
        "tools": ["Read", "Bash", "Glob", "Grep"],
    },
    "deployment": {
        "tools": ["Bash", "Read", "Glob"],
    },
    "monitor": {
        "tools": ["Bash", "Read", "Glob", "Grep"],
    },
}


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
    """Execute an agent in the background with live log streaming."""
    from maestro.agent.sdk_runner import run_sdk_with_logging

    # Mark as running
    async with get_session() as session:
        run = await session.get(AgentRun, run_id)
        if run:
            run.status = AgentRunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

    # Set API key as env var
    import os
    os.environ["ANTHROPIC_API_KEY"] = api_key

    # Create workspace directory
    workspace_path = tempfile.mkdtemp(prefix=f"maestro-agent-{run_id}-")

    # Clone repo if available
    from maestro.agent.sdk_runner import _write_log
    if repo:
        await _write_log(run_id, "status", f"Cloning repository: {repo}")
        proc = await asyncio.create_subprocess_shell(
            f"git clone https://github.com/{repo}.git {workspace_path}/repo",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            workspace_path = f"{workspace_path}/repo"
            await _write_log(run_id, "status", f"Repository cloned successfully")
        else:
            err_msg = stderr.decode(errors="replace")[:300] if stderr else "Unknown error"
            await _write_log(run_id, "error", f"Clone failed: {err_msg}")
    else:
        await _write_log(run_id, "status", "No repository configured — working in empty workspace")

    try:
        # Get system prompt from the agent module
        agent_cfg = AGENT_CONFIGS.get(plugin.name, {"tools": ["Read", "Bash"]})

        # Import the system prompt from the agent module
        system_prompt = ""
        try:
            mod = __import__(f"maestro.agent.{plugin.name}", fromlist=["SYSTEM_PROMPT"])
            system_prompt = getattr(mod, "SYSTEM_PROMPT", "")
        except (ImportError, AttributeError):
            system_prompt = f"You are the {plugin.display_name}. {plugin.description}"

        # Count previous iterations for this task (prevent infinite loops)
        from sqlalchemy import select, func as sqlfunc
        async with get_session() as session:
            iteration_count = (await session.execute(
                select(sqlfunc.count(AgentRun.id)).where(
                    AgentRun.task_pipeline_id == task_pipeline_id
                )
            )).scalar() or 0

        max_iterations = extra_config.get("max_review_iterations", 3)

        # Build prompt with context
        prompt_parts = [f"## Issue: {issue_title}"]
        if issue_description:
            prompt_parts.append(issue_description)
        if pr_url:
            prompt_parts.append(f"\nPR: {pr_url}")
            prompt_parts.append("Read the PR comments with `gh pr view --comments` to understand feedback.")
        if repo:
            prompt_parts.append(f"Repository: {repo}")

        # Add context for feedback loop
        iteration = iteration_count // 2 + 1
        if plugin.name == "implementation" and pr_url:
            pr_num = pr_url.rstrip("/").split("/")[-1] if pr_url else ""
            prompt_parts.append(
                f"\n## THIS IS A FOLLOW-UP (iteration {iteration}/{max_iterations})"
                f"\nPR #{pr_num} already exists with review comments that MUST be addressed."
                f"\n1. Checkout the PR branch: `gh pr checkout {pr_num} --repo {repo}`"
                f"\n2. List ALL review comments: `gh api repos/{repo}/pulls/{pr_num}/comments`"
                f"\n3. Address EVERY comment — do not skip any"
                f"\n4. Commit and push your fixes"
            )
        elif plugin.name == "review" and iteration > 1:
            pr_num = pr_url.rstrip("/").split("/")[-1] if pr_url else ""
            prompt_parts.append(
                f"\n## THIS IS A RE-REVIEW (iteration {iteration}/{max_iterations})"
                f"\nThe implementation agent has pushed fixes for previous review comments."
                f"\n1. List previous comments: `gh api repos/{repo}/pulls/{pr_num}/comments`"
                f"\n2. Check if EACH comment was addressed in the latest code"
                f"\n3. Resolve addressed comments, flag remaining ones"
                f"\n4. Only APPROVE if ALL comments are resolved and no new issues"
            )
        elif plugin.name == "review":
            prompt_parts.append(
                "\nThis is the first review. Be thorough. Post inline comments on specific lines."
                "\nOutput REVIEW_VERDICT: APPROVE or REVIEW_VERDICT: REQUEST_CHANGES"
            )

        prompt_parts.append("\nProceed with your task.")
        prompt = "\n".join(prompt_parts)

        # Run with live logging
        result = await run_sdk_with_logging(
            run_id=run_id,
            system_prompt=system_prompt,
            prompt=prompt,
            model=model,
            workspace_path=workspace_path,
            allowed_tools=agent_cfg["tools"],
        )

        # Update run record
        print(f"[MAESTRO] Agent run {run_id} ({plugin.name}) SDK finished: {result['status']}")
        async with get_session() as session:
            run = await session.get(AgentRun, run_id)
            if run:
                run.status = (
                    AgentRunStatus.COMPLETED
                    if result["status"] == "completed"
                    else AgentRunStatus.FAILED
                )
                run.summary = result.get("last_text", "")[:500]
                run.error = result.get("error") or ""
                run.cost_usd = result.get("total_cost_usd", 0.0)
                run.finished_at = datetime.now(timezone.utc)
                await session.commit()
                print(f"[MAESTRO] Run {run_id} status updated to {run.status}")

        # Save PR URL to pipeline record if detected
        detected_pr = result.get("pr_url", "")
        if detected_pr:
            async with get_session() as session:
                task = await session.get(TaskPipelineRecord, task_pipeline_id)
                if task and not task.pr_url:
                    task.pr_url = detected_pr
                    try:
                        task.pr_number = detected_pr.rstrip("/").split("/")[-1]
                    except (IndexError, AttributeError):
                        pass
                    await session.commit()
                    print(f"[MAESTRO] PR URL saved: {detected_pr}")

        print(f"[MAESTRO] Agent run {run_id} ({plugin.name}) finished: {result['status']}")

        # --- Auto-transition logic ---
        if result["status"] == "completed":
            try:
                print(f"[MAESTRO] Attempting auto-transition for {plugin.name} (run {run_id})")
                await _auto_transition(
                    plugin_name=plugin.name,
                    result=result,
                    workspace_id=workspace_id,
                    task_pipeline_id=task_pipeline_id,
                    issue_title=issue_title,
                    issue_description=issue_description,
                    issue_url=issue_url,
                    iteration_count=iteration_count,
                    max_iterations=max_iterations,
                )
                print(f"[MAESTRO] Auto-transition completed for {plugin.name}")
            except Exception as trans_exc:
                print(f"[MAESTRO] Auto-transition FAILED for run {run_id}: {trans_exc}")
                import traceback
                traceback.print_exc()

    except Exception as exc:
        print(f"[MAESTRO] Agent run {run_id} EXCEPTION: {exc}")
        import traceback
        traceback.print_exc()
        async with get_session() as session:
            run = await session.get(AgentRun, run_id)
            if run:
                run.status = AgentRunStatus.FAILED
                run.error = str(exc)
                run.finished_at = datetime.now(timezone.utc)
                await session.commit()


async def _auto_transition(
    plugin_name: str,
    result: dict,
    workspace_id: int,
    task_pipeline_id: int,
    issue_title: str,
    issue_description: str,
    issue_url: str,
    iteration_count: int,
    max_iterations: int,
) -> None:
    """Auto-transition pipeline status based on agent result."""
    from maestro.agent.sdk_runner import _write_log
    from maestro.db import crud

    next_status = None
    reason = ""

    if plugin_name == "implementation":
        # Implementation done → move to review
        next_status = PipelineStatus.REVIEW
        reason = "Implementation completed — moving to review"

    elif plugin_name == "review":
        # Check the verdict from agent output
        verdict = _extract_verdict(result)
        if verdict == "APPROVE":
            next_status = PipelineStatus.RISK_PROFILE
            reason = "Review approved — moving to risk profile"
        elif verdict == "REQUEST_CHANGES":
            if iteration_count < max_iterations * 2:  # *2 because each loop is impl+review
                next_status = PipelineStatus.IMPLEMENT
                reason = f"Review requested changes — sending back to implement (iteration {iteration_count // 2 + 1}/{max_iterations})"
            else:
                reason = f"Review requested changes but max iterations ({max_iterations}) reached — needs human intervention"
                logger.warning(reason)

    elif plugin_name == "risk_profile":
        import re
        all_text = re.sub(r'[*`_~]', '', result.get("all_text", "") or result.get("last_text", ""))
        upper = all_text.upper()
        if "AUTO_APPROVE: YES" in upper or "RISK_LEVEL: LOW" in upper or "RISK LEVEL: LOW" in upper:
            next_status = PipelineStatus.DEPLOY
            reason = "Risk profile: low risk, auto-approved — moving to deploy"
        elif "RISK_LEVEL: MEDIUM" in upper or "RISK_LEVEL: HIGH" in upper or "RISK_LEVEL: CRITICAL" in upper:
            reason = "Risk profile: requires human review — not auto-deploying"
            logger.info(reason)

    elif plugin_name == "deployment":
        next_status = PipelineStatus.MONITOR
        reason = "Deployment completed — moving to monitor"

    if next_status:
        logger.info("Auto-transition for task %d: %s (%s)", task_pipeline_id, next_status.value, reason)

        async with get_session() as session:
            task = await session.get(TaskPipelineRecord, task_pipeline_id)
            if task:
                task.status = next_status
                await session.commit()

        # Dispatch the next agent
        await dispatch_agent_for_status(
            workspace_id=workspace_id,
            task_pipeline_id=task_pipeline_id,
            status=next_status.value,
            issue_title=issue_title,
            issue_description=issue_description,
            issue_url=issue_url,
        )


def _extract_verdict(result: dict) -> str:
    """Extract review verdict from agent output."""
    import re
    # Use all_text to search across all messages, not just the last one
    all_text = result.get("all_text", "") or result.get("last_text", "")
    clean = re.sub(r'[*`_~]', '', all_text)
    for line in clean.split("\n"):
        line = line.strip()
        if "REVIEW_VERDICT:" in line:
            verdict = line.split("REVIEW_VERDICT:", 1)[1].strip().upper()
            # Clean any trailing markdown or punctuation
            verdict = re.sub(r'[^A-Z_]', '', verdict)
            if verdict in ("APPROVE", "REQUEST_CHANGES"):
                return verdict
    # Fallback: look for keywords in cleaned text
    upper = clean.upper()
    if "REQUEST_CHANGES" in upper or "REQUEST CHANGES" in upper:
        return "REQUEST_CHANGES"
    if "APPROVE" in upper:
        return "APPROVE"
    return "APPROVE"  # default to approve if unclear
