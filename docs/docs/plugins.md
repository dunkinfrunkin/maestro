---
sidebar_position: 6
title: Plugins
---

# Plugins

Maestro supports custom agents through a Python plugin system. Add linters, security scanners, notification hooks, or entirely new pipeline stages.

## How it works

Plugins are Python packages that register entry points. Maestro discovers all installed plugins on startup and makes them available as pipeline stages.

Each plugin implements the `AgentPlugin` interface:

```python
from maestro.plugins import AgentPlugin, TaskContext, AgentResult

class MyAgent(AgentPlugin):
    name = "my-agent"
    stage = "post_implement"

    async def execute(self, context: TaskContext) -> AgentResult:
        diff = await context.get_pr_diff()
        issues = self.analyze(diff)

        if issues:
            return AgentResult(status="needs_changes", comments=issues)
        return AgentResult(status="passed")
```

## Creating a plugin

### 1. Set up the package

```
my-maestro-plugin/
  pyproject.toml
  my_plugin/
    __init__.py
    agent.py
```

### 2. Register the entry point

In `pyproject.toml`:

```toml
[project]
name = "my-maestro-plugin"
version = "0.1.0"

[project.entry-points."maestro.agents"]
my-agent = "my_plugin.agent:MyAgent"
```

### 3. Implement the agent

```python
from maestro.plugins import AgentPlugin, TaskContext, AgentResult

class MyAgent(AgentPlugin):
    name = "my-agent"
    stage = "post_implement"

    async def execute(self, context: TaskContext) -> AgentResult:
        task = context.task
        diff = await context.get_pr_diff()
        content = await context.read_file("src/main.py")

        await context.add_comment(
            file="src/main.py",
            line=42,
            body="Consider adding error handling here.",
        )

        return AgentResult(
            status="passed",
            summary="Analysis complete. 1 suggestion added.",
        )
```

### 4. Install and run

```bash
cd my-maestro-plugin
pip install -e .
```

Restart Maestro. The plugin is discovered automatically.

## TaskContext API

| Method | Description |
|---|---|
| `context.task` | Current task object |
| `context.project` | Project configuration |
| `context.workspace` | Workspace (repo path, remote URL) |
| `await context.get_pr_diff()` | Full PR diff as string |
| `await context.read_file(path)` | Read a file from the workspace |
| `await context.list_files(glob)` | List files matching a pattern |
| `await context.add_comment(file, line, body)` | Post an inline PR comment |
| `await context.add_activity(message)` | Add to the task activity log |

## AgentResult

| Field | Type | Description |
|---|---|---|
| `status` | `str` | `"passed"`, `"needs_changes"`, or `"failed"` |
| `summary` | `str` | Human-readable summary |
| `comments` | `list` | Optional inline comments |
| `metadata` | `dict` | Optional key-value data attached to the task |

## Pipeline stages

Plugins can hook into these stages:

| Stage | When it runs |
|---|---|
| `pre_implement` | Before the Implementation Agent |
| `post_implement` | After implementation, before review |
| `pre_review` | Before the Review Agent |
| `post_review` | After review approval |
| `pre_deploy` | Before merging the PR |
| `post_deploy` | After successful deployment |

## Examples

### Linter

```python
class LinterAgent(AgentPlugin):
    name = "linter"
    stage = "post_implement"

    async def execute(self, context: TaskContext) -> AgentResult:
        import subprocess
        result = subprocess.run(
            ["ruff", "check", context.workspace.path],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return AgentResult(
                status="needs_changes",
                summary=f"Lint issues:\n{result.stdout}",
            )
        return AgentResult(status="passed", summary="No lint issues.")
```

### Slack notification

```python
class SlackNotifier(AgentPlugin):
    name = "slack-notify"
    stage = "post_deploy"

    async def execute(self, context: TaskContext) -> AgentResult:
        import httpx
        await httpx.AsyncClient().post(
            SLACK_WEBHOOK_URL,
            json={"text": f"Deployed: {context.task.title}"},
        )
        return AgentResult(status="passed", summary="Notified Slack.")
```
