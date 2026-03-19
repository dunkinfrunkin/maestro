"""Auth API routes: register, login."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from maestro.auth import create_token, get_current_user, hash_password, verify_password
from maestro.db.engine import get_session
from maestro.db.models import User

router = APIRouter(prefix="/api/v1/auth")


class RegisterRequest(BaseModel):
    email: str
    name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class UserResponse(BaseModel):
    id: int
    email: str
    name: str


@router.post("/register")
async def register(body: RegisterRequest) -> AuthResponse:
    async with get_session() as session:
        existing = await session.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            email=body.email,
            name=body.name,
            hashed_password=hash_password(body.password),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

    token = create_token(user.id, user.email)
    return AuthResponse(
        token=token,
        user=UserResponse(id=user.id, email=user.email, name=user.name),
    )


@router.post("/login")
async def login(body: LoginRequest) -> AuthResponse:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_token(user.id, user.email)
    return AuthResponse(
        token=token,
        user=UserResponse(id=user.id, email=user.email, name=user.name),
    )


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, name=user.name)
