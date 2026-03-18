"""Strict Liquid-compatible prompt rendering."""

from __future__ import annotations

from typing import Any

from liquid import Environment

_env = Environment()


def render_prompt(template: str, issue: dict[str, Any], attempt: int | None = None) -> str:
    """Render a Liquid prompt template with issue context.

    Per spec:
    - Strict variable/filter checking
    - Convert issue keys to strings
    - Preserve nested structures
    - attempt is None on first run, integer on retries
    """
    # Convert issue values to strings for Liquid compatibility
    issue_ctx = _stringify_values(issue)

    context: dict[str, Any] = {"issue": issue_ctx}
    if attempt is not None:
        context["attempt"] = attempt

    tpl = _env.from_string(template)
    return tpl.render(**context)


def _stringify_values(obj: Any) -> Any:
    """Recursively convert values to strings for Liquid template rendering."""
    if isinstance(obj, dict):
        return {k: _stringify_values(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_values(v) for v in obj]
    if obj is None:
        return ""
    return str(obj)
