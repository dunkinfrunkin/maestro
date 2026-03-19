"""Workspace and project API routes."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from maestro.auth import get_current_user
from maestro.db.engine import get_session
from maestro.db.models import Project, User, Workspace, WorkspaceMember, WorkspaceRole

router = APIRouter(prefix="/api/v1")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WorkspaceCreate(BaseModel):
    name: str


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    slug: str
    role: str
    created_at: str


class MemberResponse(BaseModel):
    id: int
    user_id: int
    email: str
    name: str
    role: str


class MemberAdd(BaseModel):
    email: str
    role: str = "member"


class ProjectCreate(BaseModel):
    name: str


class ProjectResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    slug: str
    created_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "workspace"


async def _require_member(workspace_id: int, user_id: int) -> WorkspaceMember:
    async with get_session() as session:
        result = await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    return member


async def _require_owner(workspace_id: int, user_id: int) -> WorkspaceMember:
    member = await _require_member(workspace_id, user_id)
    if member.role != WorkspaceRole.OWNER:
        raise HTTPException(status_code=403, detail="Owner access required")
    return member


# ---------------------------------------------------------------------------
# Workspaces
# ---------------------------------------------------------------------------


@router.get("/workspaces")
async def list_workspaces(user: User = Depends(get_current_user)) -> list[WorkspaceResponse]:
    async with get_session() as session:
        result = await session.execute(
            select(Workspace, WorkspaceMember)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user.id)
            .order_by(Workspace.name)
        )
        rows = result.all()
    return [
        WorkspaceResponse(
            id=ws.id,
            name=ws.name,
            slug=ws.slug,
            role=mem.role.value,
            created_at=ws.created_at.isoformat() if ws.created_at else "",
        )
        for ws, mem in rows
    ]


@router.post("/workspaces")
async def create_workspace(body: WorkspaceCreate, user: User = Depends(get_current_user)) -> WorkspaceResponse:
    slug = _slugify(body.name)
    async with get_session() as session:
        # Ensure unique slug
        existing = await session.execute(select(Workspace).where(Workspace.slug == slug))
        if existing.scalar_one_or_none():
            slug = f"{slug}-{user.id}"

        ws = Workspace(name=body.name, slug=slug)
        session.add(ws)
        await session.flush()

        member = WorkspaceMember(
            workspace_id=ws.id, user_id=user.id, role=WorkspaceRole.OWNER
        )
        session.add(member)
        await session.commit()
        await session.refresh(ws)

    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        slug=ws.slug,
        role="owner",
        created_at=ws.created_at.isoformat() if ws.created_at else "",
    )


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/members")
async def list_members(workspace_id: int, user: User = Depends(get_current_user)) -> list[MemberResponse]:
    await _require_member(workspace_id, user.id)
    async with get_session() as session:
        result = await session.execute(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
        )
        rows = result.all()
    return [
        MemberResponse(
            id=mem.id, user_id=u.id, email=u.email, name=u.name, role=mem.role.value
        )
        for mem, u in rows
    ]


@router.post("/workspaces/{workspace_id}/members")
async def add_member(workspace_id: int, body: MemberAdd, user: User = Depends(get_current_user)) -> MemberResponse:
    await _require_owner(workspace_id, user.id)

    try:
        role = WorkspaceRole(body.role)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")

    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == body.email))
        target = result.scalar_one_or_none()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")

        existing = await session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == target.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User already a member")

        mem = WorkspaceMember(workspace_id=workspace_id, user_id=target.id, role=role)
        session.add(mem)
        await session.commit()
        await session.refresh(mem)

    return MemberResponse(
        id=mem.id, user_id=target.id, email=target.email, name=target.name, role=mem.role.value
    )


@router.delete("/workspaces/{workspace_id}/members/{member_id}")
async def remove_member(workspace_id: int, member_id: int, user: User = Depends(get_current_user)) -> dict:
    await _require_owner(workspace_id, user.id)
    async with get_session() as session:
        mem = await session.get(WorkspaceMember, member_id)
        if not mem or mem.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Member not found")
        if mem.user_id == user.id:
            raise HTTPException(status_code=400, detail="Cannot remove yourself")
        await session.delete(mem)
        await session.commit()
    return {"status": "removed"}


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@router.get("/workspaces/{workspace_id}/projects")
async def list_projects(workspace_id: int, user: User = Depends(get_current_user)) -> list[ProjectResponse]:
    await _require_member(workspace_id, user.id)
    async with get_session() as session:
        result = await session.execute(
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.name)
        )
        projects = result.scalars().all()
    return [
        ProjectResponse(
            id=p.id,
            workspace_id=p.workspace_id,
            name=p.name,
            slug=p.slug,
            created_at=p.created_at.isoformat() if p.created_at else "",
        )
        for p in projects
    ]


@router.post("/workspaces/{workspace_id}/projects")
async def create_project(workspace_id: int, body: ProjectCreate, user: User = Depends(get_current_user)) -> ProjectResponse:
    await _require_member(workspace_id, user.id)
    slug = _slugify(body.name)
    async with get_session() as session:
        project = Project(workspace_id=workspace_id, name=body.name, slug=slug)
        session.add(project)
        await session.commit()
        await session.refresh(project)
    return ProjectResponse(
        id=project.id,
        workspace_id=project.workspace_id,
        name=project.name,
        slug=project.slug,
        created_at=project.created_at.isoformat() if project.created_at else "",
    )


@router.delete("/workspaces/{workspace_id}/projects/{project_id}")
async def delete_project(workspace_id: int, project_id: int, user: User = Depends(get_current_user)) -> dict:
    await _require_owner(workspace_id, user.id)
    async with get_session() as session:
        project = await session.get(Project, project_id)
        if not project or project.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Project not found")
        await session.delete(project)
        await session.commit()
    return {"status": "deleted"}
