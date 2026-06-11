"""Supabase JWT verification — the auth dependency for protected routes.

The backend never issues tokens. The frontend signs in against Supabase Auth
(GoTrue) and sends the resulting access token as ``Authorization: Bearer <jwt>``.
Here we verify that JWT's signature, audience and expiry, and expose the caller
identity via the ``get_current_user`` FastAPI dependency.

Verification uses the project's public JWKS (asymmetric ES256/RS256 — the modern
Supabase default). If ``SUPABASE_JWT_SECRET`` is set instead, the legacy shared
HS256 secret is used.
"""

from __future__ import annotations

from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core import config
from src.schemas.auth import AuthUser

# auto_error=False so a missing/!Bearer header yields a consistent 401 below
# (the default would raise 403 for a missing Authorization header).
_bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient:
    if not config.SUPABASE_JWKS_URL:
        raise RuntimeError(
            "Cannot verify auth tokens: SUPABASE_URL is not configured. "
            "Set SUPABASE_URL (or SUPABASE_JWT_SECRET) in backend/.env."
        )
    return jwt.PyJWKClient(config.SUPABASE_JWKS_URL)


def _decode(token: str) -> dict:
    """Verify and decode a Supabase access token, returning its claims."""
    # Legacy shared secret takes precedence when explicitly configured.
    if config.SUPABASE_JWT_SECRET:
        return jwt.decode(
            token,
            config.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience=config.SUPABASE_JWT_AUD,
        )
    if config.SUPABASE_JWKS_URL:
        signing_key = _jwks_client().get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["ES256", "RS256"],
            audience=config.SUPABASE_JWT_AUD,
        )
    raise RuntimeError(
        "No Supabase JWT verification method configured "
        "(set SUPABASE_URL or SUPABASE_JWT_SECRET)."
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = _decode(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing subject.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    import uuid

    try:
        user_id = uuid.UUID(str(sub))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has invalid subject.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return AuthUser(id=user_id, email=claims.get("email"))
