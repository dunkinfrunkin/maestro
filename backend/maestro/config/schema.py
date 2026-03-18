"""Typed configuration schema based on the Symphony specification."""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field, model_validator


class TrackerConfig(BaseModel):
    kind: str = "linear"
    endpoint: str = "https://api.linear.app/graphql"
    api_key: str = ""
    project_slug: str = ""
    active_states: list[str] = Field(default_factory=lambda: ["Todo", "In Progress"])
    terminal_states: list[str] = Field(default_factory=lambda: ["Done", "Canceled"])


class PollingConfig(BaseModel):
    interval_ms: int = 30000


class HookConfig(BaseModel):
    after_create: str | None = None
    before_run: str | None = None
    after_run: str | None = None
    before_remove: str | None = None
    timeout_ms: int = 60000


class WorkspaceConfig(BaseModel):
    root: str = ""

    @model_validator(mode="after")
    def _default_root(self) -> "WorkspaceConfig":
        if not self.root:
            import tempfile
            self.root = os.path.join(tempfile.gettempdir(), "maestro-workspaces")
        return self


class AgentConfig(BaseModel):
    max_concurrent_agents: int = 4
    max_retry_backoff_ms: int = 320000
    max_concurrent_agents_by_state: dict[str, int] = Field(default_factory=dict)


class CodexConfig(BaseModel):
    command: str = "codex"
    approval_policy: str = "auto-approve"
    thread_sandbox: str | None = None
    turn_sandbox_policy: str | None = None
    read_timeout_ms: int = 5000
    turn_timeout_ms: int = 3600000
    stall_timeout_ms: int = 300000


class ServerConfig(BaseModel):
    port: int | None = None
    host: str = "127.0.0.1"


class ServiceConfig(BaseModel):
    """Complete typed runtime configuration."""

    tracker: TrackerConfig = Field(default_factory=TrackerConfig)
    polling: PollingConfig = Field(default_factory=PollingConfig)
    hooks: HookConfig = Field(default_factory=HookConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    agent: AgentConfig = Field(default_factory=AgentConfig)
    codex: CodexConfig = Field(default_factory=CodexConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)

    def resolve_env_vars(self) -> "ServiceConfig":
        """Resolve $VAR references in string fields to environment values."""
        data = self.model_dump()
        _resolve_dict(data)
        return ServiceConfig.model_validate(data)


def _resolve_dict(d: dict[str, Any]) -> None:
    for k, v in d.items():
        if isinstance(v, str) and v.startswith("$"):
            env_name = v[1:]
            d[k] = os.environ.get(env_name, "")
        elif isinstance(v, dict):
            _resolve_dict(v)
        elif isinstance(v, list):
            _resolve_list(v)


def _resolve_list(lst: list[Any]) -> None:
    for i, v in enumerate(lst):
        if isinstance(v, str) and v.startswith("$"):
            env_name = v[1:]
            lst[i] = os.environ.get(env_name, "")
        elif isinstance(v, dict):
            _resolve_dict(v)
        elif isinstance(v, list):
            _resolve_list(v)
