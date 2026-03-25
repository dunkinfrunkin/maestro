"""Factory for creating tracker and code host instances.

Usage:
    tracker = create_tracker("github", token=token, repo="owner/repo")
    codehost = create_codehost("github", token=token)
"""

from __future__ import annotations

from typing import Any

from maestro.external.base import CodeHost, IssueTracker


def create_tracker(provider: str, **kwargs: Any) -> IssueTracker:
    """Create an IssueTracker instance for the given provider.

    Args:
        provider: "github", "linear", or "jira"
        **kwargs: Provider-specific arguments (token, repo, api_key, etc.)
    """
    provider = provider.lower()

    if provider == "github":
        from maestro.external.github.tracker import GitHubIssueTracker
        return GitHubIssueTracker(
            token=kwargs["token"],
            repo=kwargs.get("repo", ""),
            endpoint=kwargs.get("endpoint", "https://api.github.com"),
        )

    if provider == "linear":
        from maestro.external.linear.tracker import LinearIssueTracker
        return LinearIssueTracker(
            api_key=kwargs["api_key"],
            project_slug=kwargs["project_slug"],
            active_states=kwargs.get("active_states", []),
            terminal_states=kwargs.get("terminal_states", []),
            endpoint=kwargs.get("endpoint", "https://api.linear.app/graphql"),
        )

    if provider == "jira":
        from maestro.external.jira.tracker import JiraIssueTracker
        return JiraIssueTracker(
            base_url=kwargs["base_url"],
            api_token=kwargs["api_token"],
            project_key=kwargs["project_key"],
            email=kwargs.get("email", ""),
            active_statuses=kwargs.get("active_statuses"),
            terminal_statuses=kwargs.get("terminal_statuses"),
        )

    raise ValueError(f"Unknown tracker provider: {provider}")


def create_codehost(provider: str, **kwargs: Any) -> CodeHost:
    """Create a CodeHost instance for the given provider.

    Args:
        provider: "github" (gitlab, bitbucket in future)
        **kwargs: Provider-specific arguments (token, endpoint, etc.)
    """
    provider = provider.lower()

    if provider == "github":
        from maestro.external.github.codehost import GitHubCodeHost
        return GitHubCodeHost(
            token=kwargs["token"],
            endpoint=kwargs.get("endpoint", "https://api.github.com"),
        )

    raise ValueError(f"Unknown code host provider: {provider}")
