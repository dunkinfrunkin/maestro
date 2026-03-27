"""Auth API routes: SSO, email login, config, me."""

from __future__ import annotations

import hashlib
import os
import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from maestro.auth import create_token, get_current_user, get_oidc, is_auth_disabled
from maestro.db.models import User

_FRONTEND_URL = os.environ.get("MAESTRO_FRONTEND_URL", "")
_CALLBACK_URL = os.environ.get("MAESTRO_CALLBACK_URL", "")  # e.g. https://maestro.company.com/auth/callback

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
# Auth config — tells frontend whether SSO is available
# ---------------------------------------------------------------------------


@router.get("/config")
async def auth_config() -> AuthConfigResponse:
    if is_auth_disabled():
        return AuthConfigResponse(auth_disabled=True)
    oidc = get_oidc()
    if oidc:
        return AuthConfigResponse(
            sso_enabled=True,
            issuer=oidc.issuer,
            client_id=oidc.client_id,
        )
    return AuthConfigResponse(sso_enabled=False)


# ---------------------------------------------------------------------------
# SSO — initiate OIDC flow
# ---------------------------------------------------------------------------


@router.get("/sso")
async def sso_redirect(request: Request):
    """Redirect to OIDC provider's authorization endpoint."""
    oidc = get_oidc()
    if not oidc:
        raise HTTPException(status_code=404, detail="SSO not configured")

    # PKCE — match Kit: 32 random bytes, base64url encoded (43 chars)
    import base64
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()

    auth_endpoint = await oidc.get_authorization_endpoint()
    callback_url = _CALLBACK_URL or (str(request.base_url).rstrip("/") + "/auth/callback")

    params = {
        "client_id": oidc.client_id,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": callback_url,
        "state": "ui",
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }

    # Store PKCE verifier in cookie
    response = Response(status_code=302)
    response.headers["Location"] = auth_endpoint + "?" + urlencode(params)
    response.set_cookie(
        "maestro_pkce",
        verifier,
        path="/api/v1/auth",
        max_age=300,
        httponly=True,
        samesite="lax",
    )
    return response


# ---------------------------------------------------------------------------
# SSO callback — exchange code for token
# ---------------------------------------------------------------------------


@router.get("/callback")
async def sso_callback(request: Request):
    """Handle OIDC callback: exchange code, verify token, redirect to frontend."""
    import logging
    from fastapi.responses import RedirectResponse
    import jwt as pyjwt

    logger = logging.getLogger(__name__)

    oidc = get_oidc()
    if not oidc:
        return RedirectResponse(f"{_FRONTEND_URL}?error=SSO+not+configured")

    code = request.query_params.get("code")
    if not code:
        error = request.query_params.get("error_description") or request.query_params.get("error") or "Unknown"
        return RedirectResponse(f"{_FRONTEND_URL}?error={error}")

    verifier = request.cookies.get("maestro_pkce", "")
    callback_url = _CALLBACK_URL or (str(request.base_url).rstrip("/") + "/auth/callback")

    try:
        token_data = await oidc.exchange_code(code, callback_url, verifier)
        logger.info("Token exchange response keys: %s", list(token_data.keys()))

        id_token = token_data.get("id_token") or token_data.get("access_token")
        if not id_token:
            return RedirectResponse(f"{_FRONTEND_URL}?error=No+ID+token")

        email = await oidc.verify_id_token(id_token)

        try:
            claims = pyjwt.decode(id_token, options={"verify_signature": False})
            name = claims.get("name", "") or claims.get("given_name", "") or email.split("@")[0]
        except Exception:
            name = email.split("@")[0]

        session_token = create_token(email, name)
        logger.info("SSO login successful: %s", email)

        return RedirectResponse(
            url=f"{_FRONTEND_URL}/auth/callback#token={session_token}",
            status_code=302,
        )
    except Exception as e:
        logger.exception("SSO callback failed")
        return RedirectResponse(f"{_FRONTEND_URL}?error=SSO+failed")


# ---------------------------------------------------------------------------
# Email-only login — for development (no password)
# ---------------------------------------------------------------------------


@router.post("/login")
async def login(body: LoginRequest) -> AuthResponse:
    """Simple email login — creates user if needed. For development."""
    from sqlalchemy import select
    from maestro.db.engine import get_session
    from maestro.db.models import User

    email = body.email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email required")

    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email=email,
                name=email.split("@")[0],
                hashed_password="",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

    token = create_token(user.email, user.name)
    return AuthResponse(
        token=token,
        user=UserResponse(id=user.id, email=user.email, name=user.name),
    )


# ---------------------------------------------------------------------------
# Me — who am I
# ---------------------------------------------------------------------------


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, name=user.name)
