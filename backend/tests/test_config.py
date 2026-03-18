"""Tests for config parsing, workflow loading, and env resolution."""

from __future__ import annotations

import os
import textwrap

import pytest

from maestro.config.schema import ServiceConfig
from maestro.config.workflow import build_service_config, parse_workflow_text


def test_parse_empty_workflow():
    wf = parse_workflow_text("")
    assert wf.config == {}
    assert wf.prompt_template == ""


def test_parse_front_matter_and_body():
    text = textwrap.dedent("""\
        ---
        tracker:
          kind: linear
          api_key: $LINEAR_API_KEY
          project_slug: my-project
        polling:
          interval_ms: 10000
        ---

        You are working on issue {{ issue.identifier }}: {{ issue.title }}.
    """)
    wf = parse_workflow_text(text)
    assert wf.config["tracker"]["kind"] == "linear"
    assert wf.config["tracker"]["api_key"] == "$LINEAR_API_KEY"
    assert wf.config["polling"]["interval_ms"] == 10000
    assert "{{ issue.identifier }}" in wf.prompt_template


def test_parse_body_only():
    text = "Just a prompt, no front matter."
    wf = parse_workflow_text(text)
    assert wf.config == {}
    assert wf.prompt_template == "Just a prompt, no front matter."


def test_invalid_yaml_raises():
    text = "---\n: bad: yaml: [[\n---\nbody"
    with pytest.raises(ValueError, match="Invalid YAML"):
        parse_workflow_text(text)


def test_build_config_defaults():
    wf = parse_workflow_text("")
    cfg = build_service_config(wf)
    assert cfg.tracker.kind == "linear"
    assert cfg.polling.interval_ms == 30000
    assert cfg.agent.max_concurrent_agents == 4


def test_build_config_front_matter_overrides_defaults():
    text = textwrap.dedent("""\
        ---
        polling:
          interval_ms: 5000
        agent:
          max_concurrent_agents: 8
        ---
        prompt body
    """)
    wf = parse_workflow_text(text)
    cfg = build_service_config(wf)
    assert cfg.polling.interval_ms == 5000
    assert cfg.agent.max_concurrent_agents == 8


def test_build_config_explicit_overrides_front_matter():
    text = textwrap.dedent("""\
        ---
        polling:
          interval_ms: 5000
        ---
        prompt
    """)
    wf = parse_workflow_text(text)
    cfg = build_service_config(wf, overrides={"polling": {"interval_ms": 1000}})
    assert cfg.polling.interval_ms == 1000


def test_env_var_resolution(monkeypatch):
    monkeypatch.setenv("MY_KEY", "secret-123")
    text = textwrap.dedent("""\
        ---
        tracker:
          api_key: $MY_KEY
        ---
        prompt
    """)
    wf = parse_workflow_text(text)
    cfg = build_service_config(wf)
    assert cfg.tracker.api_key == "secret-123"


def test_env_var_missing_resolves_to_empty(monkeypatch):
    monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
    text = textwrap.dedent("""\
        ---
        tracker:
          api_key: $NONEXISTENT_VAR
        ---
        prompt
    """)
    wf = parse_workflow_text(text)
    cfg = build_service_config(wf)
    assert cfg.tracker.api_key == ""
