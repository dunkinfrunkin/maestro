"""Pipeline dispatcher — triggers agents when task status changes."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

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
from maestro.agents.plugin import registry

logger = logging.getLogger(__name__)

# Per-(task, agent) locks to prevent concurrent duplicate dispatches
_dispatch_locks: dict[tuple[int, str], asyncio.Lock] = {}


def _get_dispatch_lock(task_pipeline_id: int, agent_name: str) -> asyncio.Lock:
    key = (task_pipeline_id, agent_name)
    if key not in _dispatch_locks:
        _dispatch_locks[key] = asyncio.Lock()
    return _dispatch_locks[key]


# Map pipeline status → agent type
STATUS_TO_AGENT: dict[str, str] = {
    # New statuses
    PipelineStatus.IN_PROGRESS.value: AgentType.IMPLEMENTATION.value,
    # Legacy statuses (backward compat)
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
    issue_identifier: str = "",
    triggered_by: str = "",
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

    async with _get_dispatch_lock(task_pipeline_id, agent_name):
        return await _dispatch_agent_locked(
            agent_name=agent_name,
            plugin=plugin,
            workspace_id=workspace_id,
            task_pipeline_id=task_pipeline_id,
            status=status,
            issue_title=issue_title,
            issue_description=issue_description,
            issue_url=issue_url,
            issue_identifier=issue_identifier,
            triggered_by=triggered_by,
        )


async def _dispatch_agent_locked(
    agent_name: str,
    plugin,
    workspace_id: int,
    task_pipeline_id: int,
    status: str,
    issue_title: str = "",
    issue_description: str = "",
    issue_url: str = "",
    issue_identifier: str = "",
    triggered_by: str = "",
) -> int | None:
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

        # Check API key — use provider from agent config, fallback to anthropic
        provider = agent_config.provider if agent_config else "anthropic"
        try:
            provider_enum = ApiKeyProvider(provider)
        except ValueError:
            provider_enum = ApiKeyProvider.ANTHROPIC
        api_key_record = await crud.get_api_key(session, workspace_id, provider_enum)
        if not api_key_record:
            logger.warning("No %s API key for workspace %d, skipping agent", provider, workspace_id)
            return None
        from maestro.db.encryption import decrypt_token
        api_key = decrypt_token(api_key_record.encrypted_key)

        # Get task pipeline record for PR info
        task_record = await session.get(TaskPipelineRecord, task_pipeline_id)
        pr_url = task_record.pr_url if task_record else ""
        pr_number = task_record.pr_number if task_record else ""
        repo = task_record.repo if task_record else ""

        # Get connection info for clone auth
        conn = None
        tracker_token = ""
        if task_record:
            conn = await crud.get_connection(session, task_record.tracker_connection_id)
            if conn:
                tracker_token = crud.get_decrypted_token(conn)

        # Fetch issue title/description from tracker if not provided
        if not issue_title and task_record and conn and tracker_token:
            try:
                parts = task_record.external_ref.split(":")
                issue_id = ":".join(parts[2:]) if len(parts) >= 3 else ""
                print(f"[MAESTRO] Fetching issue from tracker: kind={conn.kind.value}, issue_id={issue_id}")
                if issue_id:
                    issue = await _fetch_issue_for_dispatch(conn, tracker_token, issue_id)
                    if issue:
                        issue_title = issue.title or ""
                        issue_description = issue.description or ""
                        issue_url = issue.url or issue_url
                        print(f"[MAESTRO] Fetched issue: title={issue_title!r}, desc_len={len(issue_description)}")
                    else:
                        print(f"[MAESTRO] Issue not found for id={issue_id}")
            except Exception as exc:
                import traceback
                print(f"[MAESTRO] Failed to fetch issue from tracker: {exc}")
                traceback.print_exc()

        # Resolve repo: task record → connection project → description/URL
        if not repo and task_record:
            if conn and conn.project:
                repo = conn.project
            # Try to extract repo from issue description or URL
            if not repo:
                repo = _extract_repo_from_text(
                    issue_description,
                    issue_url,
                    conn.kind.value if conn else "",
                    conn.endpoint if conn else "",
                )
            # Save repo back to task record for future runs
            if repo:
                task_record.repo = repo
                await session.commit()

        # Build clone URL with auth
        # If the task tracker doesn't host code (Jira, Linear), find a
        # code-hosting connection (GitHub/GitLab) that can clone this repo.
        clone_url = ""
        clone_conn = conn
        clone_token = tracker_token
        if repo and conn and conn.kind.value in ("jira", "linear"):
            all_conns = await crud.list_connections(session)
            for c in all_conns:
                if c.kind.value in ("github", "gitlab"):
                    clone_conn = c
                    clone_token = crud.get_decrypted_token(c)
                    break
        if repo and clone_conn:
            clone_url = _build_clone_url(
                repo=repo,
                tracker_kind=clone_conn.kind.value,
                endpoint=clone_conn.endpoint,
                token=clone_token,
                email=clone_conn.email,
            )

        # If the existing PR/MR is closed/merged, clear it so the agent creates a new one
        if pr_url and clone_conn and clone_token:
            pr_state = await _check_pr_state(pr_url, clone_conn, clone_token)
            if pr_state in ("closed", "merged"):
                print(f"[MAESTRO] Existing PR/MR is {pr_state}, clearing so agent creates a new one")
                pr_url = ""
                pr_number = ""
                if task_record:
                    task_record.pr_url = ""
                    task_record.pr_number = ""
                    await session.commit()

        model = agent_config.model if agent_config else "sonnet"

        # Determine code host type for prompt adaptation
        code_host = ""
        if clone_conn:
            code_host = clone_conn.kind.value  # "github" or "gitlab"

        extra = extra if agent_config else {}

        # Serialize job context for worker queue
        payload = json.dumps({
            "provider": provider,
            "model": model,
            "issue_title": issue_title,
            "issue_description": issue_description,
            "issue_url": issue_url,
            "issue_identifier": issue_identifier,
            "pr_url": pr_url,
            "pr_number": pr_number,
            "repo": repo,
            "clone_url": clone_url,
            "code_host": code_host,
            "extra_config": extra,
            "plugin_name": agent_name,
        })

        # Guard: skip if a run for this task+agent is already active
        from sqlalchemy import select as sa_select
        existing = await session.scalar(
            sa_select(AgentRun.id).where(
                AgentRun.task_pipeline_id == task_pipeline_id,
                AgentRun.agent_type == AgentType(agent_name),
                AgentRun.status.in_([AgentRunStatus.PENDING, AgentRunStatus.RUNNING]),
            ).limit(1)
        )
        if existing:
            print(f"[MAESTRO] Skipping duplicate dispatch: {agent_name} already active (run {existing}) for task {task_pipeline_id}")
            return existing

        # Create agent run record
        run = AgentRun(
            workspace_id=workspace_id,
            task_pipeline_id=task_pipeline_id,
            agent_type=AgentType(agent_name),
            status=AgentRunStatus.PENDING,
            model=model,
            triggered_by=triggered_by,
            job_payload=payload,
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    # Dispatch based on worker mode
    worker_mode = os.environ.get("MAESTRO_WORKER_MODE", "inline")
    if worker_mode == "queue":
        # Workers will pick up the PENDING job from the DB
        print(f"[MAESTRO] Run {run_id} enqueued for worker (mode=queue)")
    else:
        # Inline mode: mark RUNNING immediately so the worker process doesn't
        # also pick it up as a PENDING job and execute it a second time.
        async with get_session() as session:
            run = await session.get(AgentRun, run_id)
            if run:
                run.status = AgentRunStatus.RUNNING
                run.started_at = datetime.now(timezone.utc)
                await session.commit()

        asyncio.create_task(
            _execute_agent(
                run_id=run_id,
                plugin=plugin,
                api_key=api_key,
                provider=provider,
                model=model,
                workspace_id=workspace_id,
                task_pipeline_id=task_pipeline_id,
                issue_title=issue_title,
                issue_description=issue_description,
                issue_url=issue_url,
                issue_identifier=issue_identifier,
                pr_url=pr_url,
                pr_number=pr_number,
                repo=repo,
                clone_url=clone_url,
                code_host=code_host,
                extra_config=extra,
            )
        )

    return run_id


    # Map agent type to system prompt and tools
AGENT_CONFIGS = {
    "implementation": {
        "tools": ["Read", "Write", "Edit", "NotebookEdit", "Bash", "Glob", "Grep", "Agent", "Skill"],
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
    "requirements": {
        "tools": [],
    },
}

# Which .agents/ files each agent reads for context
AGENT_CONTEXT_FILES = {
    "implementation": [
        "SPECIFICATION.md",
        "ARCHITECTURE.md",
        "DATABASE.md",
        "STYLE_GUIDE.md",
        "SECURITY.md",
        "COMPLIANCE.md",
    ],
    "review": [
        "SPECIFICATION.md",
        "ARCHITECTURE.md",
        "STYLE_GUIDE.md",
        "SECURITY.md",
        "COMPLIANCE.md",
    ],
    "risk_profile": [
        "ARCHITECTURE.md",
        "COMPLIANCE.md",
        "DATABASE.md",
        "SECURITY.md",
        "RUNBOOK.md",
    ],
    "deployment": [
        "DEPLOY.md",
        "RUNBOOK.md",
    ],
    "monitor": [
        "MONITORING.md",
        "RUNBOOK.md",
    ],
}


def _load_agent_context(workspace_path: str, agent_name: str) -> str:
    """Load .agents/ files relevant to this agent type. Returns context string or empty."""
    agents_dir = Path(workspace_path) / ".agents"
    if not agents_dir.is_dir():
        return ""

    files = AGENT_CONTEXT_FILES.get(agent_name, [])
    if not files:
        return ""

    sections = []
    for filename in files:
        filepath = agents_dir / filename
        if filepath.is_file():
            try:
                content = filepath.read_text(encoding="utf-8").strip()
                if content and "<!-- FILL:" not in content[:200]:
                    # Skip files that haven't been populated yet
                    sections.append(f"## {filename}\n\n{content}")
            except Exception:
                pass

    if not sections:
        return ""

    return "# Repository Context (.agents/)\n\n" + "\n\n---\n\n".join(sections) + "\n\n---\n\n"


async def _execute_agent(
    run_id: int,
    plugin,
    api_key: str,
    provider: str,
    model: str,
    workspace_id: int,
    task_pipeline_id: int,
    issue_title: str,
    issue_description: str,
    issue_url: str,
    issue_identifier: str,
    pr_url: str,
    pr_number: str,
    repo: str,
    clone_url: str,
    code_host: str,
    extra_config: dict,
) -> None:
    """Execute an agent in the background with live log streaming."""
    from maestro.agents.cli_runner import run_cli_with_logging

    # Mark as running
    async with get_session() as session:
        run = await session.get(AgentRun, run_id)
        if run:
            run.status = AgentRunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

    try:
        # Set API key as env var
        import os
        os.environ["ANTHROPIC_API_KEY"] = api_key

        # Set code host token so glab/gh CLI can authenticate
        if clone_url and code_host == "gitlab":
            _set_gitlab_token_from_clone_url(clone_url)
        elif clone_url and code_host == "github":
            _set_github_token_from_clone_url(clone_url)

        # Create workspace directory
        workspace_path = tempfile.mkdtemp(prefix=f"maestro-agent-{run_id}-")

        # Clone repo if available
        from maestro.agents.sdk_runner import _write_log
        if clone_url:
            # Log repo name but not the token-embedded URL
            await _write_log(run_id, "status", f"Cloning repository: {repo}")
            proc = await asyncio.create_subprocess_exec(
                "git", "clone", "--depth", "1", clone_url, f"{workspace_path}/repo",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0:
                workspace_path = f"{workspace_path}/repo"
                await _write_log(run_id, "status", "Repository cloned successfully")
            else:
                # Sanitize error output to avoid leaking tokens
                err_msg = stderr.decode(errors="replace")[:300] if stderr else "Unknown error"
                err_msg = _sanitize_clone_error(err_msg)
                await _write_log(run_id, "error", f"Clone failed: {err_msg}")
        elif repo:
            await _write_log(run_id, "error", f"Repository '{repo}' found but could not build clone URL — check connection settings")
        else:
            await _write_log(run_id, "status", "No repository configured — working in empty workspace")
        # Get system prompt from the agent module
        agent_cfg = AGENT_CONFIGS.get(plugin.name, {"tools": ["Read", "Bash"]})

        # Get system prompt: custom from DB first, fall back to agent module default
        custom_prompt = extra_config.get("custom_prompt", "")
        if custom_prompt:
            system_prompt = (
                custom_prompt
                .replace("[ISSUE]", issue_identifier)
                .replace("[ISSUE_TITLE]", issue_title)
                .replace("[ISSUE_DESCRIPTION]", issue_description)
                .replace("[ISSUE_URL]", issue_url)
            )
        else:
            system_prompt = ""
            try:
                mod = __import__(f"maestro.agents.{plugin.name}", fromlist=["SYSTEM_PROMPT"])
                # Pick host-specific prompt if available
                if code_host == "gitlab":
                    system_prompt = getattr(mod, "SYSTEM_PROMPT_GITLAB", "") or getattr(mod, "SYSTEM_PROMPT", "")
                else:
                    system_prompt = getattr(mod, "SYSTEM_PROMPT_GITHUB", "") or getattr(mod, "SYSTEM_PROMPT", "")
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
        # Load .agents/ context files if they exist
        agent_context = _load_agent_context(workspace_path, plugin.name)
        if agent_context:
            await _write_log(run_id, "status", f"Loaded .agents/ context for {plugin.name}")

        prompt_parts = []
        if agent_context:
            prompt_parts.append(agent_context)
        prompt_parts.append(f"## Issue: {issue_title}")
        if issue_description:
            prompt_parts.append(issue_description)
        if pr_url:
            pr_num = pr_url.rstrip("/").split("/")[-1] if pr_url else ""
            prompt_parts.append(f"\n{'MR' if code_host == 'gitlab' else 'PR'}: {pr_url}")
            if code_host == "gitlab":
                # Extract and encode project path for glab API calls
                gitlab_project_encoded = ""
                if "/-/merge_requests/" in pr_url:
                    project_path = pr_url.split("/-/merge_requests/")[0].split("://", 1)[1].split("/", 1)[1]
                    gitlab_project_encoded = project_path.replace("/", "%2F")
                prompt_parts.append("This is a GitLab repository. Use `glab` (NOT `gh`) for all MR operations.")
                prompt_parts.append(f"MR number: {pr_num}")
                if gitlab_project_encoded:
                    prompt_parts.append(f"GitLab project (URL-encoded for API calls): {gitlab_project_encoded}")
                prompt_parts.append("Post inline comments directly on the MR using the glab API as described in your system prompt.")
            else:
                prompt_parts.append("Post inline review comments directly on the PR using gh as described in your system prompt.")
        if repo:
            prompt_parts.append(f"Repository: {repo}")

        # Add context for feedback loop
        iteration = iteration_count // 2 + 1
        is_gitlab = code_host == "gitlab"
        mr_or_pr = "MR" if is_gitlab else "PR"

        if plugin.name == "implementation" and pr_url:
            pr_num = pr_url.rstrip("/").split("/")[-1] if pr_url else ""
            if is_gitlab:
                prompt_parts.append(
                    f"\n## THIS IS A FOLLOW-UP (iteration {iteration}/{max_iterations})"
                    f"\n{mr_or_pr} !{pr_num} already exists with review comments that MUST be addressed."
                    f"\n1. Checkout the MR branch (check `git branch -a` for the branch name)"
                    f"\n2. Read the MR comments to understand feedback"
                    f"\n3. Address EVERY comment — do not skip any"
                    f"\n4. Commit and push your fixes"
                )
            else:
                prompt_parts.append(
                    f"\n## THIS IS A FOLLOW-UP (iteration {iteration}/{max_iterations})"
                    f"\n{mr_or_pr} #{pr_num} already exists with review comments that MUST be addressed."
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
                f"\nCheck if EACH comment was addressed in the latest code."
                f"\nOnly APPROVE if ALL comments are resolved and no new issues."
            )
        elif plugin.name == "review":
            pr_num = pr_url.rstrip("/").split("/")[-1] if pr_url else ""
            if is_gitlab and pr_url and "/-/merge_requests/" in pr_url:
                project_path = pr_url.split("/-/merge_requests/")[0].split("://", 1)[1].split("/", 1)[1]
                encoded = project_path.replace("/", "%2F")
                prompt_parts.append(
                    f"\n## REVIEW INSTRUCTIONS — YOU MUST POST INLINE COMMENTS"
                    f"\n"
                    f"\n1. Checkout: `glab mr checkout {pr_num}`"
                    f"\n2. Get SHAs: `glab api 'projects/{encoded}/merge_requests/{pr_num}' | jq -r '.diff_refs'`"
                    f"\n3. For EACH finding, post an INLINE comment with position params:"
                    f"\n```"
                    f"\nglab api --method POST 'projects/{encoded}/merge_requests/{pr_num}/discussions' \\"
                    f"\n  -f 'body=YOUR FINDING HERE' \\"
                    f"\n  -f 'position[position_type]=text' \\"
                    f"\n  -f 'position[base_sha]=BASE_SHA_HERE' \\"
                    f"\n  -f 'position[head_sha]=HEAD_SHA_HERE' \\"
                    f"\n  -f 'position[start_sha]=START_SHA_HERE' \\"
                    f"\n  -f 'position[new_path]=path/to/file.tsx' \\"
                    f"\n  -f 'position[new_line]=LINE_NUMBER'"
                    f"\n```"
                    f"\nCRITICAL: You MUST include ALL position fields. Without them the comment is NOT inline."
                    f"\nnew_line MUST be a line ADDED or CHANGED in the diff (shown with + prefix)."
                    f"\n"
                    f"\nOutput REVIEW_VERDICT: APPROVE or REVIEW_VERDICT: REQUEST_CHANGES"
                )
            elif not is_gitlab and repo:
                prompt_parts.append(
                    f"\n## REVIEW INSTRUCTIONS — YOU MUST POST INLINE COMMENTS"
                    f"\nWrite review JSON to /tmp/review.json with inline comments, then post:"
                    f"\n```"
                    f"\ncat > /tmp/review.json << 'REVIEWJSON'"
                    f'\n{{"body":"Summary","event":"REQUEST_CHANGES","comments":[{{"path":"file.tsx","line":42,"side":"RIGHT","body":"finding"}}]}}'
                    f"\nREVIEWJSON"
                    f"\ngh api repos/{repo}/pulls/{pr_num}/reviews -X POST --input /tmp/review.json"
                    f"\n```"
                    f"\nline MUST be a line ADDED or CHANGED in the diff."
                    f"\n"
                    f"\nOutput REVIEW_VERDICT: APPROVE or REVIEW_VERDICT: REQUEST_CHANGES"
                )
            else:
                prompt_parts.append(
                    "\nThis is the first review. Be thorough."
                    "\nOutput REVIEW_VERDICT: APPROVE or REVIEW_VERDICT: REQUEST_CHANGES"
                )

        prompt_parts.append("\nProceed with your task.")
        prompt = "\n".join(prompt_parts)

        print(f"[MAESTRO] Agent {plugin.name} prompt for run {run_id}: title={issue_title!r}, desc_len={len(issue_description)}, prompt_len={len(prompt)}")
        print(f"[MAESTRO] Prompt preview: {prompt[:500]}")

        # Run with live logging via Claude Code CLI
        result = await run_cli_with_logging(
            run_id=run_id,
            system_prompt=system_prompt,
            prompt=prompt,
            provider=provider,
            model=model,
            workspace_path=workspace_path,
            allowed_tools=agent_cfg["tools"],
            api_key=api_key,
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
                run.summary = result.get("last_text", "")
                run.error = result.get("error") or ""
                run.cost_usd = result.get("total_cost_usd", 0.0)
                run.input_tokens = result.get("input_tokens", 0)
                run.output_tokens = result.get("output_tokens", 0)
                run.peak_memory_mb = result.get("peak_memory_mb", 0.0)
                run.avg_cpu_percent = result.get("avg_cpu_percent", 0.0)
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


async def dispatch_requirements_agent(
    workspace_id: int,
    task_pipeline_id: int,
    issue_title: str = "",
    issue_description: str = "",
    issue_url: str = "",
    issue_identifier: str = "",
    triggered_by: str = "",
) -> int | None:
    """Dispatch the requirements agent for a task. Returns run_id or None."""
    from maestro.agents.requirements import run_requirements_agent, DEFAULT_SYSTEM_PROMPT
    from maestro.agents.cli_runner import _write_log

    plugin = registry.get("requirements")
    if not plugin:
        logger.warning("Requirements plugin not registered")
        return None

    async with get_session() as session:
        agent_config = await crud.get_agent_config(session, workspace_id, AgentType.REQUIREMENTS)
        provider = agent_config.provider if agent_config else "anthropic"
        try:
            provider_enum = ApiKeyProvider(provider)
        except ValueError:
            provider_enum = ApiKeyProvider.ANTHROPIC
        api_key_record = await crud.get_api_key(session, workspace_id, provider_enum)
        if not api_key_record:
            logger.warning("No %s API key for workspace %d, skipping requirements agent", provider, workspace_id)
            return None
        from maestro.db.encryption import decrypt_token
        api_key = decrypt_token(api_key_record.encrypted_key)
        model = agent_config.model if agent_config else "sonnet"
        extra: dict = {}
        if agent_config:
            try:
                extra = json.loads(agent_config.extra_config) if agent_config.extra_config else {}
            except (json.JSONDecodeError, TypeError):
                extra = {}

        # Resolve repo and clone URL using the same logic as other agents
        task_record = await session.get(TaskPipelineRecord, task_pipeline_id)
        repo = task_record.repo if task_record else ""
        conn = None
        tracker_token = ""
        if task_record:
            conn = await crud.get_connection(session, task_record.tracker_connection_id)
            if conn:
                tracker_token = crud.get_decrypted_token(conn)
        if not repo and task_record:
            if conn and conn.project:
                repo = conn.project
            if not repo:
                repo = _extract_repo_from_text(
                    issue_description, issue_url,
                    conn.kind.value if conn else "",
                    conn.endpoint if conn else "",
                )
            if repo:
                task_record.repo = repo
                await session.commit()
        clone_url = ""
        clone_conn = conn
        clone_token = tracker_token
        if repo and conn and conn.kind.value in ("jira", "linear"):
            all_conns = await crud.list_connections(session)
            for c in all_conns:
                if c.kind.value in ("github", "gitlab"):
                    clone_conn = c
                    clone_token = crud.get_decrypted_token(c)
                    break
        if repo and clone_conn:
            clone_url = _build_clone_url(
                repo=repo,
                tracker_kind=clone_conn.kind.value,
                endpoint=clone_conn.endpoint,
                token=clone_token,
                email=clone_conn.email,
            )

        run = AgentRun(
            workspace_id=workspace_id,
            task_pipeline_id=task_pipeline_id,
            agent_type=AgentType.REQUIREMENTS,
            status=AgentRunStatus.RUNNING,
            model=model,
            triggered_by=triggered_by,
            job_payload=json.dumps({
                "plugin_name": "requirements",
                "provider": provider,
                "model": model,
                "issue_title": issue_title,
                "issue_description": issue_description,
                "issue_url": issue_url,
                "issue_identifier": issue_identifier,
                "extra_config": extra,
            }),
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id
        run.started_at = datetime.now(timezone.utc)
        await session.commit()

    system_prompt = extra.get("custom_prompt") or DEFAULT_SYSTEM_PROMPT

    async def _run():
        import tempfile, shutil
        workspace_path = None
        try:
            workspace_path = tempfile.mkdtemp(prefix=f"maestro-requirements-{run_id}-")
            if clone_url:
                await _write_log(run_id, "status", f"Cloning repository: {repo}")
                proc = await asyncio.create_subprocess_exec(
                    "git", "clone", "--depth", "1", clone_url, f"{workspace_path}/repo",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await proc.communicate()
                if proc.returncode == 0:
                    workspace_path = f"{workspace_path}/repo"
                    await _write_log(run_id, "status", "Repository cloned successfully")
                else:
                    err = _sanitize_clone_error(stderr.decode(errors="replace")[:300] if stderr else "")
                    await _write_log(run_id, "error", f"Clone failed: {err} — continuing without repo")

            result = await run_requirements_agent(
                run_id=run_id,
                issue_title=issue_title,
                issue_description=issue_description,
                issue_identifier=issue_identifier,
                system_prompt=system_prompt,
                api_key=api_key,
                model=model,
                cwd=workspace_path,
            )
            # If finalized, update the JIRA ticket
            if result.updated_description and issue_identifier:
                try:
                    async with get_session() as session:
                        task_record = await session.get(TaskPipelineRecord, task_pipeline_id)
                        if task_record:
                            conn = await crud.get_connection(session, task_record.tracker_connection_id)
                            if conn and conn.kind.value == "jira":
                                from maestro.external.jira.tracker import JiraIssueTracker
                                token = crud.get_decrypted_token(conn)
                                tracker = JiraIssueTracker(
                                    base_url=conn.endpoint,
                                    api_token=token,
                                    project_key="",
                                    email=conn.email,
                                )
                                await tracker.update_issue(issue_identifier, result.updated_description)
                                await tracker.close()
                                await _write_log(run_id, "status", f"Updated JIRA ticket {issue_identifier}")
                except Exception as exc:
                    logger.exception("Failed to update JIRA ticket %s", issue_identifier)
                    await _write_log(run_id, "error", f"Failed to update JIRA: {exc}")

            async with get_session() as session:
                run_obj = await session.get(AgentRun, run_id)
                if run_obj:
                    run_obj.status = AgentRunStatus.COMPLETED if result.status == "completed" else AgentRunStatus.FAILED
                    run_obj.cost_usd = result.total_cost_usd
                    run_obj.input_tokens = result.input_tokens
                    run_obj.output_tokens = result.output_tokens
                    run_obj.error = result.error or ""
                    run_obj.summary = "Requirements finalized" if result.updated_description else ""
                    run_obj.finished_at = datetime.now(timezone.utc)
                    await session.commit()
        except Exception as exc:
            logger.exception("Requirements agent task error for run %d", run_id)
            async with get_session() as session:
                run_obj = await session.get(AgentRun, run_id)
                if run_obj:
                    run_obj.status = AgentRunStatus.FAILED
                    run_obj.error = str(exc)
                    run_obj.finished_at = datetime.now(timezone.utc)
                    await session.commit()
        finally:
            if workspace_path:
                try:
                    shutil.rmtree(workspace_path, ignore_errors=True)
                except Exception:
                    pass

    asyncio.create_task(_run())
    return run_id


async def _post_review_comment(
    pr_url: str,
    code_host: str,
    review_text: str,
    run_id: int,
) -> None:
    """Post the review agent's findings as a comment on the MR/PR."""
    import shutil

    # Prefix with Maestro header and append footer
    comment = f"**Maestro Review Agent** (run #{run_id})\n\n{review_text}\n\n---\n*Created by Maestro*"

    if code_host == "gitlab":
        # Extract project path and MR number from URL
        # e.g. https://gitlab.example.com/group/project/-/merge_requests/82
        parts = pr_url.split("/-/merge_requests/")
        if len(parts) != 2:
            print(f"[MAESTRO] Cannot parse GitLab MR URL: {pr_url}")
            return
        mr_number = parts[1].rstrip("/").split("?")[0]
        project_path = parts[0].split("://", 1)[1].split("/", 1)[1]  # strip host
        encoded_project = project_path.replace("/", "%2F")

        glab_path = shutil.which("glab")
        if not glab_path:
            print("[MAESTRO] glab not found, cannot post review comment")
            return

        proc = await asyncio.create_subprocess_exec(
            glab_path, "api", "--method", "POST",
            f"projects/{encoded_project}/merge_requests/{mr_number}/notes",
            "-f", f"body={comment}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            print(f"[MAESTRO] Posted review comment to GitLab MR !{mr_number}")
        else:
            err = stderr.decode("utf-8", errors="replace")[:300]
            print(f"[MAESTRO] Failed to post GitLab comment: {err}")
    else:
        # GitHub — use gh api
        # e.g. https://github.com/owner/repo/pull/123
        parts = pr_url.split("/pull/")
        if len(parts) != 2:
            print(f"[MAESTRO] Cannot parse GitHub PR URL: {pr_url}")
            return
        pr_number = parts[1].rstrip("/").split("?")[0]
        repo_path = parts[0].split("github.com/", 1)[1]

        gh_path = shutil.which("gh")
        if not gh_path:
            print("[MAESTRO] gh not found, cannot post review comment")
            return

        proc = await asyncio.create_subprocess_exec(
            gh_path, "api",
            f"repos/{repo_path}/issues/{pr_number}/comments",
            "-f", f"body={comment}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode == 0:
            print(f"[MAESTRO] Posted review comment to GitHub PR #{pr_number}")
        else:
            err = stderr.decode("utf-8", errors="replace")[:300]
            print(f"[MAESTRO] Failed to post GitHub comment: {err}")


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
    from maestro.agents.sdk_runner import _write_log
    from maestro.db import crud

    next_status = None
    reason = ""

    if plugin_name == "implementation":
        # Check if risk profile has already run for this task
        risk_already_ran = await _has_completed_agent_type(task_pipeline_id, "risk_profile")
        if risk_already_ran:
            # Risk already done - go straight to review
            next_status = PipelineStatus.REVIEW
            reason = "Implementation completed (risk profile already done) - moving to review"
        else:
            # First implementation - run risk profile before review
            next_status = PipelineStatus.RISK_PROFILE
            reason = "Implementation completed - moving to risk profile (runs once)"

    elif plugin_name == "risk_profile":
        # Risk profile done - now move to review
        next_status = PipelineStatus.REVIEW
        reason = "Risk profile completed - moving to review"

    elif plugin_name == "review":
        verdict = _extract_verdict(result)

        if verdict == "APPROVE":
            has_unresolved = await _check_unresolved_comments(task_pipeline_id)
            if has_unresolved:
                verdict = "REQUEST_CHANGES"
                print(f"[MAESTRO] Overriding APPROVE -> REQUEST_CHANGES: unresolved inline comments exist")

        if verdict == "APPROVE":
            next_status = PipelineStatus.PENDING_APPROVAL
            reason = "Review approved - moving to pending approval (human gate)"
        elif verdict == "REQUEST_CHANGES":
            if iteration_count < max_iterations * 2:
                next_status = PipelineStatus.IMPLEMENT
                reason = f"Review requested changes - sending back to implement (iteration {iteration_count // 2 + 1}/{max_iterations})"
            else:
                reason = f"Review requested changes but max iterations ({max_iterations}) reached - needs human intervention"
                logger.warning(reason)

    elif plugin_name == "deployment":
        # Deployment stages not yet implemented - mark done for now
        next_status = PipelineStatus.DONE
        reason = "Deployment completed - done"

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


async def _has_completed_agent_type(task_pipeline_id: int, agent_type: str) -> bool:
    """Check if an agent of the given type has already completed for this task."""
    async with get_session() as session:
        stmt = (
            select(AgentRun)
            .where(AgentRun.task_pipeline_id == task_pipeline_id)
            .where(AgentRun.agent_type == AgentType(agent_type))
            .where(AgentRun.status == AgentRunStatus.COMPLETED)
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None


async def _check_unresolved_comments(task_pipeline_id: int) -> bool:
    """Check if the PR has unresolved inline review comments.

    A comment is considered resolved if it has at least one reply
    (the implementation agent replies with 'Fixed: ...' and/or
    the review agent replies with 'Verified').
    """
    try:
        async with get_session() as session:
            task = await session.get(TaskPipelineRecord, task_pipeline_id)
        if not task or not task.pr_url or not task.repo:
            return False

        pr_number = task.pr_url.rstrip("/").split("/")[-1]
        repo = task.repo

        # Get all inline comments with their replies
        proc = await asyncio.create_subprocess_exec(
            "gh", "api", f"repos/{repo}/pulls/{pr_number}/comments",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return False

        import json
        comments = json.loads(stdout.decode())

        # Find top-level comments (not replies themselves)
        # A comment is a reply if it has in_reply_to_id set
        top_level = [c for c in comments if not c.get("in_reply_to_id")]
        replies_by_parent = {}
        for c in comments:
            parent = c.get("in_reply_to_id")
            if parent:
                replies_by_parent.setdefault(parent, []).append(c)

        unresolved = 0
        for comment in top_level:
            comment_id = comment["id"]
            has_replies = len(replies_by_parent.get(comment_id, [])) > 0
            if not has_replies:
                unresolved += 1

        if unresolved > 0:
            print(f"[MAESTRO] Found {unresolved} unresolved inline comments (no replies) on PR #{pr_number}")
            return True

        print(f"[MAESTRO] All {len(top_level)} inline comments have replies — considered resolved")
        return False
    except Exception as exc:
        print(f"[MAESTRO] Error checking comments: {exc}")
        return False


def _extract_verdict(result: dict) -> str:
    """Extract review verdict from agent output."""
    import re

    # Also check the review_verdict field from cli_runner (most reliable)
    cli_verdict = (result.get("review_verdict") or "").strip().upper()
    if cli_verdict in ("APPROVE", "REQUEST_CHANGES"):
        print(f"[MAESTRO] Verdict from cli_runner: {cli_verdict}")
        return cli_verdict

    # Search all_text for REVIEW_VERDICT: marker
    all_text = result.get("all_text", "") or result.get("last_text", "")
    clean = re.sub(r'[*`~]', '', all_text)  # Don't strip underscores — needed for REVIEW_VERDICT
    for line in clean.split("\n"):
        line = line.strip()
        if "REVIEW_VERDICT:" in line:
            verdict = line.split("REVIEW_VERDICT:", 1)[1].strip().upper()
            verdict = re.sub(r'[^A-Z_]', '', verdict)
            if verdict in ("APPROVE", "REQUEST_CHANGES"):
                print(f"[MAESTRO] Verdict from text: {verdict}")
                return verdict

    # Fallback: look for REQUEST_CHANGES first (safer default)
    upper = clean.upper()
    if "REQUEST_CHANGES" in upper or "REQUEST CHANGES" in upper:
        return "REQUEST_CHANGES"

    # Default to REQUEST_CHANGES if unclear — safer than auto-approving
    print("[MAESTRO] No clear verdict found, defaulting to REQUEST_CHANGES")
    return "REQUEST_CHANGES"


# ---------------------------------------------------------------------------
# Repo resolution helpers
async def _check_pr_state(pr_url: str, conn, token: str) -> str:
    """Check if a PR/MR is open, closed, or merged. Returns state string."""
    import httpx

    try:
        if "/-/merge_requests/" in pr_url:
            # GitLab MR — extract project path and MR iid from URL
            # URL format: https://gitlab.example.com/group/project/-/merge_requests/123
            parts = pr_url.split("/-/merge_requests/")
            if len(parts) != 2:
                return "unknown"
            mr_iid = parts[1].rstrip("/")
            project_url = parts[0]
            # Extract project path from URL
            endpoint = conn.endpoint.rstrip("/") if conn.endpoint else "https://gitlab.com"
            project_path = project_url.replace(endpoint + "/", "")
            encoded_path = __import__("urllib.parse", fromlist=["quote"]).quote(project_path, safe="")
            async with httpx.AsyncClient(
                base_url=f"{endpoint}/api/v4",
                headers={"PRIVATE-TOKEN": token, "Accept": "application/json"},
                timeout=10.0,
            ) as http:
                resp = await http.get(f"/projects/{encoded_path}/merge_requests/{mr_iid}")
                resp.raise_for_status()
                data = resp.json()
                return data.get("state", "unknown")  # "opened", "closed", "merged"

        elif "/pull/" in pr_url:
            # GitHub PR — extract owner/repo and PR number
            # URL format: https://github.com/owner/repo/pull/123
            import re
            match = re.search(r"github\.com/([^/]+/[^/]+)/pull/(\d+)", pr_url)
            if not match:
                return "unknown"
            repo_path, pr_num = match.group(1), match.group(2)
            endpoint = conn.endpoint or "https://api.github.com"
            async with httpx.AsyncClient(
                base_url=endpoint,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
                timeout=10.0,
            ) as http:
                resp = await http.get(f"/repos/{repo_path}/pulls/{pr_num}")
                resp.raise_for_status()
                data = resp.json()
                state = data.get("state", "unknown")  # "open", "closed"
                if data.get("merged"):
                    return "merged"
                return state
    except Exception as exc:
        print(f"[MAESTRO] Failed to check PR/MR state: {exc}")
        return "unknown"

    return "unknown"


async def _fetch_issue_for_dispatch(conn, token: str, issue_id: str):
    """Fetch a single issue from any tracker by ID. Handles Jira numeric IDs."""
    from maestro.db.models import TrackerKind

    if conn.kind == TrackerKind.JIRA:
        from maestro.external.jira.tracker import JiraIssueTracker
        client = JiraIssueTracker(
            base_url=conn.endpoint or "https://jira.atlassian.net",
            api_token=token,
            project_key=conn.project or "",
            email=conn.email,
        )
        try:
            # Use JQL to fetch by id (numeric) or key (PROJ-123)
            if "-" in issue_id:
                jql = f'key = "{issue_id}"'
            else:
                jql = f"id = {issue_id}"
            issues = await client._search(jql, max_results=1)
            return issues[0] if issues else None
        finally:
            await client.close()

    # For other trackers, use the existing _fetch_single_issue
    from maestro.api.tasks import _fetch_single_issue
    return await _fetch_single_issue(conn, token, issue_id)


# ---------------------------------------------------------------------------

import re as _re

# Patterns that match repo paths in URLs and text
_GITHUB_REPO_RE = _re.compile(r"github\.com[/:]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git|/|#|\s|$)")
_GITLAB_REPO_RE = _re.compile(r"gitlab\.com[/:]([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+?)(?:\.git|/-/|/|#|\s|$)")
_GENERIC_GIT_RE = _re.compile(r"(?:https?://[^/]+/|git@[^:]+:)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git|/|#|\s|$)")


def _extract_repo_from_text(description: str, url: str, tracker_kind: str, endpoint: str) -> str:
    """Try to extract a repository path from issue description or URL.

    Looks for patterns like:
    - https://github.com/owner/repo
    - https://gitlab.com/group/subgroup/repo
    - git@github.com:owner/repo.git
    - owner/repo (in description text near keywords like "repo", "repository")
    """
    texts = [description or "", url or ""]
    combined = "\n".join(texts)

    if not combined.strip():
        return ""

    # Try tracker-specific patterns first
    if tracker_kind == "github":
        match = _GITHUB_REPO_RE.search(combined)
        if match:
            return match.group(1).rstrip(".")
    elif tracker_kind == "gitlab":
        # For GitLab, also check the endpoint domain
        if endpoint:
            domain = endpoint.rstrip("/").split("//")[-1]
            gitlab_re = _re.compile(
                _re.escape(domain) + r"[/:]([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+?)(?:\.git|/-/|/|#|\s|$)"
            )
            match = gitlab_re.search(combined)
            if match:
                return match.group(1).rstrip(".")
        match = _GITLAB_REPO_RE.search(combined)
        if match:
            return match.group(1).rstrip(".")

    # Generic: try any git URL
    match = _GENERIC_GIT_RE.search(combined)
    if match:
        return match.group(1).rstrip(".")

    return ""


def _set_gitlab_token_from_clone_url(clone_url: str) -> None:
    """Extract the GitLab token from the clone URL and set GITLAB_TOKEN env var."""
    import os
    from urllib.parse import urlparse
    parsed = urlparse(clone_url)
    if parsed.password:
        os.environ["GITLAB_TOKEN"] = parsed.password
    elif parsed.username and parsed.username != "oauth2":
        os.environ["GITLAB_TOKEN"] = parsed.username


def _set_github_token_from_clone_url(clone_url: str) -> None:
    """Extract the GitHub token from the clone URL and set GH_TOKEN env var."""
    import os
    from urllib.parse import urlparse
    parsed = urlparse(clone_url)
    if parsed.password:
        os.environ["GH_TOKEN"] = parsed.password
    elif parsed.username and "@" not in parsed.username:
        os.environ["GH_TOKEN"] = parsed.username


def _build_clone_url(repo: str, tracker_kind: str, endpoint: str, token: str, email: str) -> str:
    """Build an authenticated HTTPS clone URL for any tracker type.

    Args:
        repo: Repository path (e.g., "owner/repo" or "group/subgroup/repo")
        tracker_kind: "github", "gitlab", "jira", etc.
        endpoint: Base URL of the tracker (e.g., "https://gitlab.com")
        token: API token for authentication
        email: User email (used for Jira/Bitbucket basic auth)
    """
    if not repo or not token:
        return ""

    if tracker_kind == "github":
        host = "github.com"
        if endpoint and "github.com" not in endpoint:
            # GitHub Enterprise
            host = endpoint.rstrip("/").split("//")[-1]
        return f"https://x-access-token:{token}@{host}/{repo}.git"

    elif tracker_kind == "gitlab":
        host = "gitlab.com"
        if endpoint:
            host = endpoint.rstrip("/").split("//")[-1]
        return f"https://oauth2:{token}@{host}/{repo}.git"

    elif tracker_kind == "jira":
        # Jira doesn't host code — but the repo field might point to a GitHub/GitLab repo
        # Try to infer from the repo path
        if "github.com" in repo or "github" in repo.lower():
            clean = _re.sub(r"https?://github\.com/", "", repo)
            return f"https://x-access-token:{token}@github.com/{clean}.git"
        # Default: assume it's a path on the endpoint host (Bitbucket etc.)
        return ""

    return ""


def _sanitize_clone_error(error: str) -> str:
    """Remove tokens/credentials from git clone error messages."""
    # Replace anything that looks like a token in a URL
    sanitized = _re.sub(r"(https?://)[^@]+@", r"\1***@", error)
    return sanitized
