"""Authentication: OIDC/SSO, JWT sessions, API tokens.

Approach matches Kit: PKCE cookie + manual token exchange.
No session middleware, no state validation. PKCE is the CSRF protection.

No passwords. Email is the identity.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from maestro.db.engine import get_session
from maestro.db.models import User

logger = logging.getLogger(__name__)

_SECRET = os.environ.get("MAESTRO_SECRET", "dev-secret-change-me")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_DAYS = 30
_AUTH_DISABLED = os.environ.get("MAESTRO_AUTH_DISABLED", "").lower() in ("true", "1", "yes")

OIDC_ISSUER = os.environ.get("MAESTRO_OIDC_ISSUER", "")
OIDC_CLIENT_ID = os.environ.get("MAESTRO_OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.environ.get("MAESTRO_OIDC_CLIENT_SECRET", "")

# Cached OIDC discovery
_discovery: dict | None = None


def is_auth_disabled() -> bool:
    return _AUTH_DISABLED


def is_oidc_configured() -> bool:
    return bool(OIDC_ISSUER and OIDC_CLIENT_ID)


# ---------------------------------------------------------------------------
# OIDC discovery (cached)
# ---------------------------------------------------------------------------


async def get_discovery() -> dict:
    global _discovery
    if _discovery:
        return _discovery
    url = f"{OIDC_ISSUER.rstrip('/')}/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        _discovery = resp.json()
    return _discovery


# ---------------------------------------------------------------------------
# PKCE — matches Kit exactly
# ---------------------------------------------------------------------------


def generate_pkce_verifier() -> str:
    """32 random bytes, base64url encoded (43 chars). Same as Kit."""
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()


def pkce_challenge(verifier: str) -> str:
    """SHA256 of verifier, base64url encoded. Same as Kit."""
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


# ---------------------------------------------------------------------------
# Token exchange — matches Kit exactly
# ---------------------------------------------------------------------------


async def exchange_code(code: str, redirect_uri: str, verifier: str) -> dict:
    """Exchange authorization code for tokens. Form-urlencoded POST, like Kit."""
    disc = await get_discovery()
    token_endpoint = disc["token_endpoint"]

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": OIDC_CLIENT_ID,
    }
    if verifier:
        data["code_verifier"] = verifier
    if OIDC_CLIENT_SECRET:
        data["client_secret"] = OIDC_CLIENT_SECRET

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_endpoint,
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        body = resp.json()
        if resp.status_code != 200:
            error = body.get("error_description") or body.get("error") or str(body)
            raise ValueError(f"Token exchange failed ({resp.status_code}): {error}")
        return body


def extract_email_from_id_token(id_token: str) -> tuple[str, str]:
    """Decode ID token (trusted — from direct server exchange) and return (email, name)."""
    claims = jwt.decode(id_token, options={"verify_signature": False}, algorithms=["RS256", "HS256"])
    email = claims.get("email") or claims.get("preferred_username") or claims.get("sub") or ""
    name = claims.get("name", "") or claims.get("given_name", "") or ""
    return email, name


# ---------------------------------------------------------------------------
# JWT — self-signed session tokens
# ---------------------------------------------------------------------------


def create_token(email: str, name: str = "") -> str:
    payload = {
        "email": email,
        "name": name,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=_JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, _SECRET, algorithm=_JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# API tokens — maestro_ prefix, SHA256 hashed
# ---------------------------------------------------------------------------


def generate_api_token() -> str:
    return "maestro_" + secrets.token_hex(32)


def hash_api_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# FastAPI dependency — authenticate request
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=not _AUTH_DISABLED))],
) -> User:
    if _AUTH_DISABLED:
        return await _get_or_create_dev_user()

    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials
    email: str | None = None
    name: str = ""

    # Try self-signed JWT
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_JWT_ALGORITHM])
        email = payload.get("email")
        name = payload.get("name", "")
    except jwt.InvalidTokenError:
        pass

    # Try API token
    if not email and token.startswith("maestro_"):
        token_hash = hash_api_token(token)
        async with get_session() as session:
            from maestro.db.models import ApiKey
            result = await session.execute(
                select(ApiKey).where(ApiKey.encrypted_token == token_hash)
            )
            api_key = result.scalar_one_or_none()
            if api_key:
                user = await session.get(User, api_key.workspace_id)
                if user:
                    return user

    if not email:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Find or create user
    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            user = User(email=email, name=name or email.split("@")[0], hashed_password="")
            session.add(user)
            await session.commit()
            await session.refresh(user)

    return user


async def _get_or_create_dev_user() -> User:
    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == "dev@maestro.local"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(email="dev@maestro.local", name="Dev User", hashed_password="")
            session.add(user)
            await session.commit()
            await session.refresh(user)
    return user
