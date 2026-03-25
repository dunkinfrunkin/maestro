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

router = APIRouter(prefix="/api/v1/auth")


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

    # PKCE
    verifier = secrets.token_urlsafe(64)
    challenge = (
        __import__("base64")
        .urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )

    auth_endpoint = await oidc.get_authorization_endpoint()
    callback_url = str(request.base_url).rstrip("/") + "/api/v1/auth/callback"

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


@router.get("/callback", response_class=HTMLResponse)
async def sso_callback(request: Request):
    """Handle OIDC callback: exchange code, verify token, create session."""
    oidc = get_oidc()
    if not oidc:
        raise HTTPException(status_code=404, detail="SSO not configured")

    code = request.query_params.get("code")
    if not code:
        error = request.query_params.get("error_description") or request.query_params.get("error") or "Unknown error"
        raise HTTPException(status_code=400, detail=f"SSO failed: {error}")

    # Get PKCE verifier from cookie
    verifier = request.cookies.get("maestro_pkce", "")

    callback_url = str(request.base_url).rstrip("/") + "/api/v1/auth/callback"

    # Exchange code for tokens
    try:
        token_data = await oidc.exchange_code(code, callback_url, verifier)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {e}")

    id_token = token_data.get("id_token") or token_data.get("access_token")
    if not id_token:
        raise HTTPException(status_code=500, detail="No ID token in response")

    # Verify and extract email
    try:
        email = await oidc.verify_id_token(id_token)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Token verification failed: {e}")

    # Extract name from ID token if available
    import jwt as pyjwt
    try:
        claims = pyjwt.decode(id_token, options={"verify_signature": False})
        name = claims.get("name", "") or claims.get("given_name", "") or email.split("@")[0]
    except Exception:
        name = email.split("@")[0]

    # Create session JWT
    session_token = create_token(email, name)

    # Return HTML that stores token and redirects to dashboard
    # (Same pattern as Kit)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Maestro</title></head>
<body style="background:#f5f0e8;color:#2c2416;font-family:Inter,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center">
<h2 style="color:#16a34a;margin-bottom:8px">Signed in as {email}</h2>
<p style="color:#8a7e6b">Redirecting to dashboard...</p>
</div>
<script>
localStorage.setItem('maestro-token','{session_token}');
setTimeout(function(){{window.location.href='/'}},800);
</script></body></html>"""


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
