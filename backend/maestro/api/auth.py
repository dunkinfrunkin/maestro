"""Auth API routes — matches Kit's approach exactly.

SSO redirect: PKCE verifier in httponly cookie, redirect to IdP.
Callback: read verifier from cookie, exchange code, return HTML that
sets localStorage and redirects. No session middleware, no state
validation. PKCE is the CSRF protection.
"""

from __future__ import annotations

import logging
import os
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from maestro.auth import (
    OIDC_CLIENT_ID,
    OIDC_ISSUER,
    create_token,
    exchange_code,
    extract_email_from_id_token,
    generate_pkce_verifier,
    get_current_user,
    get_discovery,
    is_auth_disabled,
    is_oidc_configured,
    pkce_challenge,
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
        return AuthConfigResponse(sso_enabled=True, issuer=OIDC_ISSUER, client_id=OIDC_CLIENT_ID)
    return AuthConfigResponse(sso_enabled=False)


# ---------------------------------------------------------------------------
# SSO redirect — matches Kit: PKCE cookie, redirect to IdP
# ---------------------------------------------------------------------------


@router.get("/sso")
async def sso_redirect(request: Request):
    if not is_oidc_configured():
        raise HTTPException(status_code=404, detail="SSO not configured")

    disc = await get_discovery()
    auth_endpoint = disc["authorization_endpoint"]

    verifier = generate_pkce_verifier()
    challenge = pkce_challenge(verifier)

    callback_url = _CALLBACK_URL or (str(request.base_url).rstrip("/") + "/auth/callback")

    params = {
        "client_id": OIDC_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": callback_url,
        "state": "ui",  # static, not validated — PKCE is the protection
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }

    response = Response(status_code=302)
    response.headers["Location"] = auth_endpoint + "?" + urlencode(params)
    response.set_cookie(
        "maestro_pkce",
        verifier,
        path="/",
        max_age=300,
        httponly=True,
        samesite="lax",
    )
    return response


# ---------------------------------------------------------------------------
# SSO callback — matches Kit: read cookie, exchange code, return HTML
# ---------------------------------------------------------------------------


@router.get("/callback", response_class=HTMLResponse)
async def sso_callback(request: Request):
    if not is_oidc_configured():
        return _error_html("SSO not configured")

    code = request.query_params.get("code")
    if not code:
        error = request.query_params.get("error_description") or request.query_params.get("error") or "Unknown error"
        return _error_html(f"SSO failed: {error}")

    # Read PKCE verifier from cookie
    verifier = request.cookies.get("maestro_pkce", "")
    if not verifier:
        return _error_html("Missing PKCE verifier cookie")

    callback_url = _CALLBACK_URL or (str(request.base_url).rstrip("/") + "/auth/callback")

    # Exchange code for tokens
    try:
        token_data = await exchange_code(code, callback_url, verifier)
    except Exception as e:
        logger.exception("Token exchange failed")
        return _error_html(f"Token exchange failed: {e}")

    # Get ID token
    id_token = token_data.get("id_token") or token_data.get("access_token")
    if not id_token:
        return _error_html("No ID token in response")

    # Extract email and name
    try:
        email, name = extract_email_from_id_token(id_token)
    except Exception as e:
        logger.exception("Failed to decode ID token")
        return _error_html(f"Failed to decode token: {e}")

    if not email:
        return _error_html("No email in token")

    if not name:
        name = email.split("@")[0]

    # Create session JWT
    session_token = create_token(email, name)
    logger.info("SSO login successful: %s", email)

    # Return HTML that stores token and redirects — same pattern as Kit
    frontend_url = _FRONTEND_URL or ""
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Maestro</title></head>
<body style="background:#f5f0e8;color:#2c2416;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center">
<h2 style="color:#16a34a;margin-bottom:8px">Signed in as {email}</h2>
<p style="color:#8a7e6b">Redirecting to dashboard...</p>
</div>
<script>
localStorage.setItem('maestro-token','{session_token}');
setTimeout(function(){{window.location.href='{frontend_url}/'}},800);
</script></body></html>""")


def _error_html(message: str) -> HTMLResponse:
    frontend_url = _FRONTEND_URL or ""
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Maestro</title></head>
<body style="background:#f5f0e8;color:#2c2416;font-family:system-ui,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center">
<h2 style="color:#dc2626;margin-bottom:8px">Authentication failed</h2>
<p style="color:#8a7e6b">{message}</p>
<p><a href="{frontend_url}/" style="color:#6b5b3e">Back to login</a></p>
</div></body></html>""", status_code=400)


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
    return AuthResponse(token=token, user=UserResponse(id=user.id, email=user.email, name=user.name))


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, name=user.name)
