"""SQLAlchemy models for tracker connections and task pipeline status."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TrackerKind(str, enum.Enum):
    GITHUB = "github"
    LINEAR = "linear"


class PipelineStatus(str, enum.Enum):
    QUEUED = "queued"
    IMPLEMENT = "implement"
    REVIEW = "review"
    RISK_PROFILE = "risk_profile"
    DEPLOY = "deploy"
    MONITOR = "monitor"


class TrackerConnection(Base):
    """Stores tracker credentials (token encrypted at rest)."""

    __tablename__ = "tracker_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[TrackerKind] = mapped_column(Enum(TrackerKind), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # For GitHub: "owner/repo" (optional, blank = all repos), for Linear: project slug
    project: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    endpoint: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    encrypted_token: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TaskPipelineRecord(Base):
    """Tracks a task's position in our harness engineering pipeline.

    Only created when a user first moves a task into the pipeline.
    The task's tracker data (title, description, etc.) is NOT stored here —
    it's always fetched live from the tracker.
    """

    __tablename__ = "task_pipeline"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Tracker-agnostic identifier: "{tracker_kind}:{external_id}"
    external_ref: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    tracker_connection_id: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[PipelineStatus] = mapped_column(
        Enum(PipelineStatus), nullable=False, default=PipelineStatus.QUEUED
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
