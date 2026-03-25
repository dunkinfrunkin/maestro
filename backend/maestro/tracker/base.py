"""Backwards-compatible re-export — use maestro.external.base instead."""

from maestro.external.base import IssueTracker as TrackerClient  # noqa: F401

__all__ = ["TrackerClient"]
