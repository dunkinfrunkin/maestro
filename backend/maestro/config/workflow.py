"""WORKFLOW.md parser — YAML front matter + Liquid-compatible prompt template."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from maestro.config.schema import ServiceConfig

# Matches YAML front matter delimited by ---
_FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)", re.DOTALL)


@dataclass
class WorkflowDefinition:
    """Parsed WORKFLOW.md: config (from front matter) + prompt_template (body)."""

    config: dict[str, Any] = field(default_factory=dict)
    prompt_template: str = ""
    source_path: str = ""


def parse_workflow(path: str | Path) -> WorkflowDefinition:
    """Parse a WORKFLOW.md file into config dict + prompt template string."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    return parse_workflow_text(text, source_path=str(path))


def parse_workflow_text(text: str, source_path: str = "") -> WorkflowDefinition:
    """Parse WORKFLOW.md content from a string."""
    match = _FRONT_MATTER_RE.match(text)
    if match:
        raw_yaml = match.group(1)
        body = match.group(2)
        try:
            config = yaml.safe_load(raw_yaml) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML front matter: {exc}") from exc
    else:
        config = {}
        body = text

    return WorkflowDefinition(
        config=config,
        prompt_template=body.strip(),
        source_path=source_path,
    )


def build_service_config(
    workflow: WorkflowDefinition,
    overrides: dict[str, Any] | None = None,
) -> ServiceConfig:
    """Build a ServiceConfig by merging: defaults < front matter < overrides < env resolution.

    This implements the spec's config precedence:
        built-in defaults → YAML front matter → explicit overrides → $VAR resolution
    """
    merged: dict[str, Any] = {}

    # Layer 1: front matter
    for key in ("tracker", "polling", "hooks", "workspace", "agent", "codex", "server"):
        if key in workflow.config:
            merged[key] = workflow.config[key]

    # Layer 2: explicit overrides
    if overrides:
        for key, val in overrides.items():
            if isinstance(val, dict) and key in merged and isinstance(merged[key], dict):
                merged[key] = {**merged[key], **val}
            else:
                merged[key] = val

    # Build config (defaults fill in gaps), then resolve $VAR references
    cfg = ServiceConfig.model_validate(merged)
    return cfg.resolve_env_vars()
