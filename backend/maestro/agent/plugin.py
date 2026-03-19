"""Plugin framework for custom enterprise agents.

Enterprises can create custom agents by:
1. Subclassing AgentPlugin
2. Registering via entry points or the plugins directory
3. Plugins appear in the Agents tab alongside built-in agents

Example plugin:

    from maestro.agent.plugin import AgentPlugin, PluginResult

    class MyCustomAgent(AgentPlugin):
        name = "custom_qa"
        display_name = "QA Agent"
        description = "Runs end-to-end QA tests"
        trigger_status = "review"

        async def run(self, context: dict) -> PluginResult:
            # Your agent logic here
            return PluginResult(status="completed", summary="All tests passed")

Register in pyproject.toml:

    [project.entry-points."maestro.plugins"]
    custom_qa = "my_package.qa_agent:MyCustomAgent"
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ENTRY_POINT_GROUP = "maestro.plugins"
PLUGINS_DIR_ENV = "MAESTRO_PLUGINS_DIR"


# ---------------------------------------------------------------------------
# Plugin interface
# ---------------------------------------------------------------------------


@dataclass
class PluginResult:
    """Standard result returned by any agent plugin."""
    status: str = "completed"  # completed, failed
    summary: str = ""
    data: dict[str, Any] = field(default_factory=dict)
    messages: list[dict[str, Any]] = field(default_factory=list)
    total_cost_usd: float = 0.0
    error: str | None = None


class AgentPlugin(ABC):
    """Base class for all agent plugins (built-in and custom).

    Subclass this and implement the `run` method to create a custom agent.
    """

    # --- Class attributes (override in subclass) ---
    name: str = ""                    # unique identifier (e.g., "implementation")
    display_name: str = ""            # human-readable name
    description: str = ""             # short description
    trigger_status: str = ""          # pipeline status that triggers this agent
    icon: str = ""                    # heroicon path data (optional)
    configurable_fields: list[dict[str, Any]] = []  # extra config schema

    @abstractmethod
    async def run(self, context: dict[str, Any]) -> PluginResult:
        """Execute the agent.

        Context dict includes:
        - api_key: str (Anthropic API key)
        - model: str (selected model ID)
        - workspace_path: str (working directory)
        - issue_title: str
        - issue_description: str
        - pr_url: str (if applicable)
        - pr_number: str (if applicable)
        - extra_config: dict (agent-specific config from DB)

        Returns PluginResult with status and details.
        """
        ...

    def validate_config(self, extra_config: dict[str, Any]) -> list[str]:
        """Validate agent-specific configuration. Returns list of error messages."""
        return []


# ---------------------------------------------------------------------------
# Built-in agent plugins (wrappers around existing agents)
# ---------------------------------------------------------------------------


class ImplementationPlugin(AgentPlugin):
    name = "implementation"
    display_name = "Implementation Agent"
    description = "Reads issues, writes code, creates PRs"
    trigger_status = "implement"

    async def run(self, context: dict[str, Any]) -> PluginResult:
        from maestro.agent.implementation import run_implementation_agent
        result = await run_implementation_agent(
            api_key=context["api_key"],
            model=context["model"],
            workspace_path=context["workspace_path"],
            issue_title=context.get("issue_title", ""),
            issue_description=context.get("issue_description", ""),
            repo_url=context.get("repo_url"),
        )
        return PluginResult(
            status=result.status,
            summary=f"Implementation {'completed' if result.status == 'completed' else 'failed'}",
            messages=result.messages,
            total_cost_usd=result.total_cost_usd,
            error=result.error,
        )


class ReviewPlugin(AgentPlugin):
    name = "review"
    display_name = "Review Agent"
    description = "Thorough PR review — code quality, correctness, tests, security"
    trigger_status = "review"

    async def run(self, context: dict[str, Any]) -> PluginResult:
        from maestro.agent.review import run_review_agent
        result = await run_review_agent(
            api_key=context["api_key"],
            model=context["model"],
            workspace_path=context["workspace_path"],
            pr_url=context.get("pr_url", ""),
            pr_title=context.get("issue_title", ""),
            pr_description=context.get("issue_description", ""),
        )
        return PluginResult(
            status=result.status,
            summary=f"Review verdict: {result.verdict}",
            data={"verdict": result.verdict},
            messages=result.messages,
            total_cost_usd=result.total_cost_usd,
            error=result.error,
        )


class RiskProfilePlugin(AgentPlugin):
    name = "risk_profile"
    display_name = "Risk Profile Agent"
    description = "Scores PR risk — auto-approves low risk, escalates medium/high to humans"
    trigger_status = "risk_profile"
    configurable_fields = [
        {
            "key": "auto_approve_threshold",
            "label": "Auto-approve threshold",
            "type": "select",
            "options": ["low", "medium", "high"],
            "default": "low",
        }
    ]

    async def run(self, context: dict[str, Any]) -> PluginResult:
        from maestro.agent.risk_profile import run_risk_profile_agent
        extra = context.get("extra_config", {})
        result = await run_risk_profile_agent(
            api_key=context["api_key"],
            model=context["model"],
            workspace_path=context["workspace_path"],
            pr_url=context.get("pr_url", ""),
            pr_title=context.get("issue_title", ""),
            pr_description=context.get("issue_description", ""),
            auto_approve_threshold=extra.get("auto_approve_threshold", "low"),
        )
        return PluginResult(
            status=result.status,
            summary=f"Risk: {result.risk_level} (score: {result.risk_score:.1f}), auto-approve: {result.auto_approve}",
            data={
                "risk_level": result.risk_level,
                "risk_score": result.risk_score,
                "auto_approve": result.auto_approve,
            },
            messages=result.messages,
            total_cost_usd=result.total_cost_usd,
            error=result.error,
        )


class DeploymentPlugin(AgentPlugin):
    name = "deployment"
    display_name = "Deployment Agent"
    description = "Merges PR, monitors CI/CD pipeline, posts status updates"
    trigger_status = "deploy"

    async def run(self, context: dict[str, Any]) -> PluginResult:
        from maestro.agent.deployment import run_deployment_agent
        extra = context.get("extra_config", {})
        result = await run_deployment_agent(
            api_key=context["api_key"],
            model=context["model"],
            workspace_path=context["workspace_path"],
            pr_url=context.get("pr_url", ""),
            pr_title=context.get("issue_title", ""),
            pr_number=context.get("pr_number", ""),
            slack_webhook=extra.get("slack_webhook"),
        )
        return PluginResult(
            status=result.status,
            summary=f"Deploy: {result.deploy_status} — {result.deploy_detail}",
            data={"deploy_status": result.deploy_status, "merged": result.merged},
            messages=result.messages,
            total_cost_usd=result.total_cost_usd,
            error=result.error,
        )


class MonitorPlugin(AgentPlugin):
    name = "monitor"
    display_name = "Monitor Agent"
    description = "Checks logs, metrics, and alerts post-deployment"
    trigger_status = "monitor"

    async def run(self, context: dict[str, Any]) -> PluginResult:
        from maestro.agent.monitor import run_monitor_agent
        extra = context.get("extra_config", {})
        result = await run_monitor_agent(
            api_key=context["api_key"],
            model=context["model"],
            workspace_path=context["workspace_path"],
            deployment_ref=context.get("deployment_ref", ""),
            pr_title=context.get("issue_title", ""),
            pr_url=context.get("pr_url"),
            monitoring_endpoints=extra.get("monitoring_endpoints"),
            log_commands=extra.get("log_commands"),
        )
        return PluginResult(
            status=result.status,
            summary=f"Health: {result.monitor_status} ({result.issues_found} issues, {result.p0_count} P0)",
            data={
                "monitor_status": result.monitor_status,
                "issues_found": result.issues_found,
                "p0_count": result.p0_count,
            },
            messages=result.messages,
            total_cost_usd=result.total_cost_usd,
            error=result.error,
        )


# ---------------------------------------------------------------------------
# Plugin Registry
# ---------------------------------------------------------------------------


class PluginRegistry:
    """Discovers, loads, and manages agent plugins."""

    def __init__(self) -> None:
        self._plugins: dict[str, AgentPlugin] = {}

    def register(self, plugin: AgentPlugin) -> None:
        """Register a plugin instance."""
        if not plugin.name:
            raise ValueError(f"Plugin {plugin.__class__.__name__} has no name")
        if plugin.name in self._plugins:
            logger.warning("Plugin %s already registered, overwriting", plugin.name)
        self._plugins[plugin.name] = plugin
        logger.info("Registered plugin: %s (%s)", plugin.name, plugin.display_name)

    def get(self, name: str) -> AgentPlugin | None:
        return self._plugins.get(name)

    def list_all(self) -> list[AgentPlugin]:
        return list(self._plugins.values())

    def load_builtins(self) -> None:
        """Register all built-in agent plugins."""
        for cls in [
            ImplementationPlugin,
            ReviewPlugin,
            RiskProfilePlugin,
            DeploymentPlugin,
            MonitorPlugin,
        ]:
            self.register(cls())

    def load_entry_points(self) -> None:
        """Discover and load plugins from Python entry points."""
        try:
            eps = importlib.metadata.entry_points()
            group = eps.get(ENTRY_POINT_GROUP, []) if isinstance(eps, dict) else eps.select(group=ENTRY_POINT_GROUP)
            for ep in group:
                try:
                    plugin_cls = ep.load()
                    if isinstance(plugin_cls, type) and issubclass(plugin_cls, AgentPlugin):
                        self.register(plugin_cls())
                    else:
                        logger.warning("Entry point %s is not an AgentPlugin subclass", ep.name)
                except Exception:
                    logger.exception("Failed to load plugin entry point: %s", ep.name)
        except Exception:
            logger.exception("Failed to discover plugin entry points")

    def load_plugins_dir(self) -> None:
        """Load plugins from a directory (set via MAESTRO_PLUGINS_DIR env var)."""
        plugins_dir = os.environ.get(PLUGINS_DIR_ENV)
        if not plugins_dir:
            return

        path = Path(plugins_dir)
        if not path.is_dir():
            logger.warning("Plugins directory does not exist: %s", plugins_dir)
            return

        import importlib.util
        for py_file in sorted(path.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(
                    f"maestro_plugin_{py_file.stem}", py_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    # Find AgentPlugin subclasses in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, AgentPlugin)
                            and attr is not AgentPlugin
                            and attr.name
                        ):
                            self.register(attr())
            except Exception:
                logger.exception("Failed to load plugin from: %s", py_file)


# Global registry singleton
registry = PluginRegistry()


def init_plugins() -> None:
    """Initialize the plugin registry with built-in and custom plugins."""
    registry.load_builtins()
    registry.load_entry_points()
    registry.load_plugins_dir()
    logger.info("Plugin registry: %d agents loaded", len(registry.list_all()))
