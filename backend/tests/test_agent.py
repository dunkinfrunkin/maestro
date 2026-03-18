"""Tests for prompt rendering and agent runner."""

from __future__ import annotations

import json
import textwrap

import pytest

from maestro.agent.prompt import render_prompt
from maestro.agent.runner import AgentRunner, TurnResult


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------


def test_render_basic():
    template = "Work on {{ issue.identifier }}: {{ issue.title }}"
    result = render_prompt(template, {"identifier": "PROJ-1", "title": "Fix bug"})
    assert result == "Work on PROJ-1: Fix bug"


def test_render_with_attempt():
    template = "{% if attempt %}Retry #{{ attempt }}. {% endif %}Fix {{ issue.identifier }}"
    assert render_prompt(template, {"identifier": "X-1"}, attempt=None) == "Fix X-1"
    assert render_prompt(template, {"identifier": "X-1"}, attempt=3) == "Retry #3. Fix X-1"


def test_render_nested_issue():
    template = "Labels: {{ issue.labels }}"
    result = render_prompt(template, {"labels": ["bug", "urgent"]})
    assert "bug" in result


def test_render_null_field():
    template = "Desc: {{ issue.description }}"
    result = render_prompt(template, {"description": None})
    assert result == "Desc: "


# ---------------------------------------------------------------------------
# Agent runner (with mock agent subprocess)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_runner_turn_completed(tmp_path):
    # Create a mock agent script that does the handshake and completes
    script = tmp_path / "mock_agent.sh"
    script.write_text(textwrap.dedent("""\
        #!/bin/bash
        # Read initialize request from stdin
        read -r line
        # Send initialize response
        echo '{"jsonrpc":"2.0","id":1,"result":{"thread_id":"t1"}}'
        # Send turn completed
        echo '{"method":"turn/completed","params":{}}'
    """))
    script.chmod(0o755)

    runner = AgentRunner(
        command=str(script),
        read_timeout_ms=5000,
        turn_timeout_ms=10000,
        stall_timeout_ms=5000,
    )

    outcome = await runner.run_turn(
        workspace=tmp_path,
        prompt="Do something",
    )

    assert outcome.result == TurnResult.COMPLETED
    assert outcome.session.thread_id == "t1"
    assert outcome.error is None


@pytest.mark.asyncio
async def test_agent_runner_turn_failed(tmp_path):
    script = tmp_path / "mock_agent.sh"
    script.write_text(textwrap.dedent("""\
        #!/bin/bash
        read -r line
        echo '{"jsonrpc":"2.0","id":1,"result":{"thread_id":"t2"}}'
        echo '{"method":"turn/failed","params":{"error":"something broke"}}'
    """))
    script.chmod(0o755)

    runner = AgentRunner(command=str(script), read_timeout_ms=5000)
    outcome = await runner.run_turn(workspace=tmp_path, prompt="Do something")

    assert outcome.result == TurnResult.FAILED
    assert "something broke" in (outcome.error or "")


@pytest.mark.asyncio
async def test_agent_runner_no_response(tmp_path):
    script = tmp_path / "mock_agent.sh"
    script.write_text("#!/bin/bash\nexit 0\n")
    script.chmod(0o755)

    runner = AgentRunner(command=str(script), read_timeout_ms=1000)
    outcome = await runner.run_turn(workspace=tmp_path, prompt="Hello")

    assert outcome.result == TurnResult.FAILED
    assert "No initialize response" in (outcome.error or "")


@pytest.mark.asyncio
async def test_agent_runner_input_required_kills(tmp_path):
    script = tmp_path / "mock_agent.sh"
    script.write_text(textwrap.dedent("""\
        #!/bin/bash
        read -r line
        echo '{"jsonrpc":"2.0","id":1,"result":{"thread_id":"t3"}}'
        echo '{"method":"turn/input_required","params":{}}'
        sleep 60
    """))
    script.chmod(0o755)

    runner = AgentRunner(command=str(script), read_timeout_ms=5000)
    outcome = await runner.run_turn(workspace=tmp_path, prompt="Hello")

    assert outcome.result == TurnResult.FAILED
    assert "user input" in (outcome.error or "").lower()
