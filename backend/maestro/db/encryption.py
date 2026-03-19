"""Fernet-based encryption for storing tokens at rest."""

from __future__ import annotations

import os

from cryptography.fernet import Fernet

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = os.environ.get("MAESTRO_ENCRYPTION_KEY", "")
        if not key:
            raise RuntimeError(
                "MAESTRO_ENCRYPTION_KEY not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        _fernet = Fernet(key.encode())
    return _fernet


def encrypt_token(token: str) -> str:
    """Encrypt a token string, return base64-encoded ciphertext."""
    return _get_fernet().encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    """Decrypt a base64-encoded ciphertext back to plaintext."""
    return _get_fernet().decrypt(encrypted.encode()).decode()
