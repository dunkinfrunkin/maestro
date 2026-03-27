"""Auth API routes: SSO via Authlib, email login, config, me."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from maestro.auth import (
    create_token,
    get_current_user,
    is_auth_disabled,
    is_oidc_configured,
    oauth,
    _OIDC_ISSUER,
    _OIDC_CLIENT_ID,
    _SECRET,
)
from maestro.db.models import User

logger = logging.getLogger(__name__)

_FRONTEND_URL = os.environ.get("MAESTRO_FRONTEND_URL", "")
_CALLBACK_URL = os.environ.get("MAESTRO_CALLBACK_URL", "")

router = APIRouter(prefix="/auth")


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class AuthConfigResponse(BaseModel):
    auth_disabled: bool = False
    sso_enabled: bool = False
    issuer: str | None = None
    client_id: str | None = None


class LoginRequest(BaseModel):
    email: str


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class UserResponse(BaseModel):
    id: int
    email: str
    name: str


# ---------------------------------------------------------------------------
# Auth config
# ---------------------------------------------------------------------------


@router.get("/config")
async def auth_config() -> AuthConfigResponse:
    if is_auth_disabled():
        return AuthConfigResponse(auth_disabled=True)
    if is_oidc_configured():
        return AuthConfigResponse(
            sso_enabled=True,
            issuer=_OIDC_ISSUER,
            client_id=_OIDC_CLIENT_ID,
        )
    return AuthConfigResponse(sso_enabled=False)


# ---------------------------------------------------------------------------
# SSO — Authlib handles PKCE, discovery, token exchange, everything
# ---------------------------------------------------------------------------


@router.get("/sso")
async def sso_redirect(request: Request):
    """Redirect to OIDC provider. Authlib handles PKCE automatically."""
    if not is_oidc_configured():
        raise HTTPException(status_code=404, detail="SSO not configured")

    callback_url = _CALLBACK_URL or (str(request.base_url).rstrip("/") + "/auth/callback")
    return await oauth.oidc.authorize_redirect(request, callback_url)


@router.get("/callback")
async def sso_callback(request: Request):
    """Handle OIDC callback. Authlib handles code exchange + PKCE verification."""
    if not is_oidc_configured():
        return RedirectResponse(f"{_FRONTEND_URL}?error=SSO+not+configured")

    try:
        token = await oauth.oidc.authorize_access_token(request)
    except Exception as e:
        logger.exception("OIDC token exchange failed")
        return RedirectResponse(f"{_FRONTEND_URL}?error={e}")

    # Extract user info from the ID token
    userinfo = token.get("userinfo")
    if not userinfo:
        # Fallback: decode ID token claims
        import jwt as pyjwt
        id_token = token.get("id_token", "")
        try:
            userinfo = pyjwt.decode(id_token, options={"verify_signature": False})
        except Exception:
            return RedirectResponse(f"{_FRONTEND_URL}?error=No+user+info")

    email = userinfo.get("email") or userinfo.get("preferred_username") or userinfo.get("sub")
    if not email:
        return RedirectResponse(f"{_FRONTEND_URL}?error=No+email+in+token")

    name = userinfo.get("name", "") or userinfo.get("given_name", "") or email.split("@")[0]

    session_token = create_token(email, name)
    logger.info("SSO login successful: %s", email)

    # Redirect to frontend callback page which stores the token
    return RedirectResponse(
        url=f"{_FRONTEND_URL}/auth/callback#token={session_token}",
        status_code=302,
    )


# ---------------------------------------------------------------------------
# Email-only login — for development
# ---------------------------------------------------------------------------


@router.post("/login")
async def login(body: LoginRequest) -> AuthResponse:
    from sqlalchemy import select
    from maestro.db.engine import get_session

    email = body.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            user = User(email=email, name=email.split("@")[0], hashed_password="")
            session.add(user)
            await session.commit()
            await session.refresh(user)

    token = create_token(user.email, user.name)
    return AuthResponse(
        token=token,
        user=UserResponse(id=user.id, email=user.email, name=user.name),
    )


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, name=user.name)
