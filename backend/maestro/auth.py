"""Authentication: OIDC/SSO via Authlib, JWT sessions, API tokens.

Three auth methods (tried in order):
1. API tokens (maestro_ prefix, SHA256 hashed)
2. Self-signed JWT (HMAC-SHA256, signed with MAESTRO_SECRET)
3. OIDC tokens (handled by Authlib)

No passwords. Email is the identity.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from authlib.integrations.starlette_client import OAuth
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


# ---------------------------------------------------------------------------
# OAuth / OIDC via Authlib
# ---------------------------------------------------------------------------

oauth = OAuth()

_OIDC_ISSUER = os.environ.get("MAESTRO_OIDC_ISSUER", "")
_OIDC_CLIENT_ID = os.environ.get("MAESTRO_OIDC_CLIENT_ID", "")
_OIDC_CLIENT_SECRET = os.environ.get("MAESTRO_OIDC_CLIENT_SECRET", "")


def init_oidc() -> bool:
    """Register OIDC provider with Authlib if configured."""
    if not _OIDC_ISSUER or not _OIDC_CLIENT_ID:
        logger.info("OIDC not configured — email-only login available")
        return False

    oauth.register(
        name="oidc",
        client_id=_OIDC_CLIENT_ID,
        client_secret=_OIDC_CLIENT_SECRET or None,
        server_metadata_url=f"{_OIDC_ISSUER.rstrip('/')}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
        code_challenge_method="S256",
    )
    logger.info("OIDC configured via Authlib: issuer=%s", _OIDC_ISSUER)
    return True


def is_oidc_configured() -> bool:
    return "oidc" in oauth._clients  # noqa: SLF001


def is_auth_disabled() -> bool:
    return _AUTH_DISABLED


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


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


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
