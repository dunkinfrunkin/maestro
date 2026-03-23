---
sidebar_position: 5
title: Plugins
---

# Plugin Framework

Maestro supports custom agents through a Python plugin system. You can add linters, security scanners, notification hooks, or entirely new pipeline stages.

## How plugins work

Plugins are Python packages that register entry points. When Maestro starts, it discovers all installed plugins and makes them available as pipeline stages.

Each plugin implements a simple interface:

```python
from maestro.plugins import AgentPlugin, TaskContext, AgentResult

class MyCustomAgent(AgentPlugin):
    """A custom agent that runs after implementation."""

    name = "my-custom-agent"
    stage = "post_implement"  # when in the pipeline to run

    async def execute(self, context: TaskContext) -> AgentResult:
        # Your logic here
        pr_diff = await context.get_pr_diff()

        # Do something with the diff
        issues = self.analyze(pr_diff)

        if issues:
            return AgentResult(
                status="needs_changes",
                comments=issues,
            )

        return AgentResult(status="passed")
```

## Creating a plugin

### 1. Create a Python package

```
my-maestro-plugin/
  pyproject.toml
  my_plugin/
    __init__.py
    agent.py
```

### 2. Define the entry point

In `pyproject.toml`:

```toml
[project]
name = "my-maestro-plugin"
version = "0.1.0"

[project.entry-points."maestro.agents"]
my-custom-agent = "my_plugin.agent:MyCustomAgent"
```

### 3. Implement the agent

In `my_plugin/agent.py`:

```python
from maestro.plugins import AgentPlugin, TaskContext, AgentResult

class MyCustomAgent(AgentPlugin):
    name = "my-custom-agent"
    stage = "post_implement"

    async def execute(self, context: TaskContext) -> AgentResult:
        # Access task metadata
        task = context.task
        project = context.project
        workspace = context.workspace

        # Access the PR diff
        diff = await context.get_pr_diff()

        # Access files in the workspace
        content = await context.read_file("src/main.py")

        # Leave comments on the PR
        await context.add_comment(
            file="src/main.py",
            line=42,
            body="Consider adding error handling here.",
        )

        return AgentResult(
            status="passed",
            summary="Custom analysis complete. 1 suggestion added.",
        )
```

### 4. Install the plugin

```bash
cd my-maestro-plugin
pip install -e .
```

Restart Maestro and the plugin will be discovered automatically.

## Plugin API

### TaskContext

The `TaskContext` object provides access to everything the agent needs:

| Method | Description |
|--------|-------------|
| `context.task` | The current task object |
| `context.project` | The project configuration |
| `context.workspace` | The workspace (repo path, remote URL) |
| `await context.get_pr_diff()` | Get the full PR diff as a string |
| `await context.read_file(path)` | Read a file from the workspace |
| `await context.list_files(glob)` | List files matching a glob pattern |
| `await context.add_comment(file, line, body)` | Add an inline PR comment |
| `await context.add_activity(message)` | Add an entry to the task activity log |

### AgentResult

Return an `AgentResult` to indicate the outcome:

| Field | Type | Description |
|-------|------|-------------|
| `status` | `str` | `"passed"`, `"needs_changes"`, or `"failed"` |
| `summary` | `str` | Human-readable summary of what the agent did |
| `comments` | `list` | Optional list of inline comments |
| `metadata` | `dict` | Optional key-value data to attach to the task |

### Pipeline stages

Plugins can hook into these stages:

| Stage | When it runs |
|-------|-------------|
| `pre_implement` | Before the implementation agent |
| `post_implement` | After implementation, before review |
| `pre_review` | Before the review agent |
| `post_review` | After review approval |
| `pre_deploy` | Before merging the PR |
| `post_deploy` | After successful deployment |

## Example plugins

### Linter plugin

```python
class LinterAgent(AgentPlugin):
    name = "linter"
    stage = "post_implement"

    async def execute(self, context: TaskContext) -> AgentResult:
        import subprocess
        result = subprocess.run(
            ["ruff", "check", context.workspace.path],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return AgentResult(
                status="needs_changes",
                summary=f"Linter found issues:\n{result.stdout}",
            )
        return AgentResult(status="passed", summary="No lint issues.")
```

### Slack notification plugin

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
        return AgentResult(status="passed", summary="Slack notification sent.")
```
