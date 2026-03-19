"""SQLAlchemy models for auth, workspaces, projects, connections, and pipeline."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


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


class WorkspaceRole(str, enum.Enum):
    OWNER = "owner"
    MEMBER = "member"


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[WorkspaceRole] = mapped_column(Enum(WorkspaceRole), nullable=False, default=WorkspaceRole.MEMBER)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "slug", name="uq_workspace_project_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ---------------------------------------------------------------------------
# Tracker Connections (scoped to workspace)
# ---------------------------------------------------------------------------


class TrackerConnection(Base):
    __tablename__ = "tracker_connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    kind: Mapped[TrackerKind] = mapped_column(Enum(TrackerKind), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    project: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    endpoint: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    encrypted_token: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Task Pipeline (scoped to project)
# ---------------------------------------------------------------------------


class TaskPipelineRecord(Base):
    __tablename__ = "task_pipeline"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    external_ref: Mapped[str] = mapped_column(String(512), nullable=False)
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

    __table_args__ = (
        UniqueConstraint("project_id", "external_ref", name="uq_project_external_ref"),
    )


# ---------------------------------------------------------------------------
# API Keys (provider keys stored encrypted, scoped to workspace)
# ---------------------------------------------------------------------------


class ApiKeyProvider(str, enum.Enum):
    ANTHROPIC = "anthropic"


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint("workspace_id", "provider", name="uq_workspace_provider"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[ApiKeyProvider] = mapped_column(Enum(ApiKeyProvider), nullable=False)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Agent Configuration (per workspace)
# ---------------------------------------------------------------------------


class AgentType(str, enum.Enum):
    IMPLEMENTATION = "implementation"
    REVIEW = "review"
    RISK_PROFILE = "risk_profile"
    DEPLOYMENT = "deployment"
    MONITOR = "monitor"


class AgentConfig(Base):
    __tablename__ = "agent_configs"
    __table_args__ = (
        UniqueConstraint("workspace_id", "agent_type", name="uq_workspace_agent_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    agent_type: Mapped[AgentType] = mapped_column(Enum(AgentType), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False, default="claude-sonnet-4-6")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
