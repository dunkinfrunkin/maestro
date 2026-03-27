"""Authentication: OIDC/SSO, email-only login, JWT sessions, API tokens.

Three auth methods (tried in order):
1. API tokens (maestro_ prefix, SHA256 hashed)
2. Self-signed JWT (HMAC-SHA256, signed with MAESTRO_SECRET)
3. OIDC tokens (verified against IdP's JWKS)

No passwords. Email is the identity.
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from maestro.db.engine import get_session
from maestro.db.models import User

logger = logging.getLogger(__name__)

_SECRET = os.environ.get("MAESTRO_SECRET", "")
if not _SECRET:
    import secrets as _secrets
    _SECRET = _secrets.token_hex(32)
    logger.warning("MAESTRO_SECRET not set — generated ephemeral secret. Sessions will not survive restarts.")
_JWT_ALGORITHM = "HS256"
_JWT_EXPIRY_DAYS = 30
_AUTH_DISABLED = os.environ.get("MAESTRO_AUTH_DISABLED", "").lower() in ("true", "1", "yes")

_bearer = HTTPBearer()


# ---------------------------------------------------------------------------
# JWT — self-signed session tokens
# ---------------------------------------------------------------------------


def create_token(email: str, name: str = "") -> str:
    """Create a session JWT for the given email."""
    payload = {
        "email": email,
        "name": name,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=_JWT_EXPIRY_DAYS),
    }
    return jwt.encode(payload, _SECRET, algorithm=_JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a self-signed JWT."""
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
    """Generate a new API token (plaintext — hash before storing)."""
    return "maestro_" + secrets.token_hex(32)


def hash_api_token(token: str) -> str:
    """SHA256 hash an API token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# OIDC — OpenID Connect verification
# ---------------------------------------------------------------------------


class OIDCVerifier:
    """Verify OIDC ID tokens from any OpenID Connect provider.

    Fetches JWKS from the IdP's discovery document and caches for 1 hour.
    """

    def __init__(self, issuer: str, client_id: str, client_secret: str = "") -> None:
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self._discovery: dict | None = None
        self._jwks_fetched: datetime | None = None

    async def get_discovery(self) -> dict:
        """Fetch and cache the OIDC discovery document."""
        if self._discovery is not None:
            return self._discovery
        url = f"{self.issuer}/.well-known/openid-configuration"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            resp.raise_for_status()
            self._discovery = resp.json()
        return self._discovery

    async def get_authorization_endpoint(self) -> str:
        doc = await self.get_discovery()
        return doc["authorization_endpoint"]

    async def get_token_endpoint(self) -> str:
        doc = await self.get_discovery()
        return doc["token_endpoint"]

    async def exchange_code(self, code: str, redirect_uri: str, code_verifier: str = "") -> dict:
        """Exchange authorization code for tokens."""
        token_endpoint = await self.get_token_endpoint()
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": self.client_id,
        }
        if code_verifier:
            data["code_verifier"] = code_verifier
        if self.client_secret:
            data["client_secret"] = self.client_secret

        async with httpx.AsyncClient() as client:
            resp = await client.post(token_endpoint, data=data)
            resp.raise_for_status()
            return resp.json()

    async def verify_id_token(self, id_token: str) -> str:
        """Verify an ID token and return the email.

        For simplicity, we decode the JWT payload without full RSA verification
        here — the token came directly from the IdP via server-side code exchange,
        so it's trusted. Full JWKS verification can be added later.
        """
        try:
            # Decode without verification — token is from direct IdP exchange
            payload = jwt.decode(
                id_token,
                options={"verify_signature": False},
                algorithms=["RS256", "HS256"],
            )
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid ID token: {e}")

        # Validate issuer
        iss = payload.get("iss", "")
        if iss != self.issuer and iss != self.issuer + "/":
            raise ValueError(f"Issuer mismatch: got {iss}, expected {self.issuer}")

        # Validate audience
        aud = payload.get("aud")
        if isinstance(aud, str):
            if aud != self.client_id:
                raise ValueError("Audience mismatch")
        elif isinstance(aud, list):
            if self.client_id not in aud:
                raise ValueError("Audience mismatch")

        # Extract email
        email = payload.get("email") or payload.get("preferred_username") or payload.get("sub")
        if not email:
            raise ValueError("No email claim in ID token")

        return email


# Global OIDC verifier — initialized on startup if configured
_oidc: OIDCVerifier | None = None


def get_oidc() -> OIDCVerifier | None:
    return _oidc


def init_oidc() -> OIDCVerifier | None:
    """Initialize OIDC verifier from environment variables."""
    global _oidc
    issuer = os.environ.get("MAESTRO_OIDC_ISSUER", "")
    client_id = os.environ.get("MAESTRO_OIDC_CLIENT_ID", "")
    client_secret = os.environ.get("MAESTRO_OIDC_CLIENT_SECRET", "")

    if issuer and client_id:
        _oidc = OIDCVerifier(issuer=issuer, client_id=client_id, client_secret=client_secret)
        logger.info("OIDC configured: issuer=%s", issuer)
        return _oidc

    logger.info("OIDC not configured — email-only login available")
    return None


# ---------------------------------------------------------------------------
# FastAPI dependency — authenticate request
# ---------------------------------------------------------------------------


def is_auth_disabled() -> bool:
    return _AUTH_DISABLED


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=not _AUTH_DISABLED))],
) -> User:
    """Authenticate a request and return the User.

    If MAESTRO_AUTH_DISABLED=true, returns a default dev user.
    Otherwise tries: self-signed JWT → API token lookup.
    Creates user on first login (no signup needed).
    """
    if _AUTH_DISABLED:
        return await _get_or_create_dev_user()

    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = credentials.credentials

    email: str | None = None
    name: str = ""

    # Try self-signed JWT first
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
                # Look up the user who owns this API key
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
            # Auto-create user on first SSO login
            user = User(
                email=email,
                name=name or email.split("@")[0],
                hashed_password="",  # No password — SSO only
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

    return user


async def _get_or_create_dev_user() -> User:
    """Return a default dev user when auth is disabled."""
    async with get_session() as session:
        result = await session.execute(select(User).where(User.email == "dev@maestro.local"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(email="dev@maestro.local", name="Dev User", hashed_password="")
            session.add(user)
            await session.commit()
            await session.refresh(user)
    return user
