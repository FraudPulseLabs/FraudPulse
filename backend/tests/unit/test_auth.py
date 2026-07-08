"""Unit tests for the Supabase JWT verification dependency.

These exercise the HS256 fallback path (via a monkeypatched shared secret) so no
network/JWKS access is required. The decode/claim-validation logic is identical
to the asymmetric path.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.core import auth as auth_module
from src.core import config

SECRET = "test-secret-for-unit-tests"


@pytest.fixture(autouse=True)
def use_hs256_secret(monkeypatch):
    # Force the HS256 fallback path so tests need no network/JWKS.
    monkeypatch.setattr(config, "SUPABASE_JWT_SECRET", SECRET)
    yield


def _make_token(secret: str = SECRET, **overrides) -> str:
    claims = {
        "sub": str(uuid.uuid4()),
        "email": "analyst@example.com",
        "aud": config.SUPABASE_JWT_AUD,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    claims.update(overrides)
    return jwt.encode(claims, secret, algorithm="HS256")


def _call(token: str | None):
    creds = (
        None
        if token is None
        else HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    )
    return asyncio.run(auth_module.get_current_user(creds))


def test_valid_token_returns_user():
    sub = str(uuid.uuid4())
    user = _call(_make_token(sub=sub, email="x@y.z"))
    assert str(user.id) == sub
    assert user.email == "x@y.z"


def test_missing_credentials_raises_401():
    with pytest.raises(HTTPException) as exc:
        _call(None)
    assert exc.value.status_code == 401


def test_expired_token_raises_401():
    token = _make_token(exp=datetime.now(timezone.utc) - timedelta(minutes=1))
    with pytest.raises(HTTPException) as exc:
        _call(token)
    assert exc.value.status_code == 401


def test_bad_signature_raises_401():
    token = _make_token(secret="a-different-secret")
    with pytest.raises(HTTPException) as exc:
        _call(token)
    assert exc.value.status_code == 401


def test_wrong_audience_raises_401():
    token = _make_token(aud="some-other-audience")
    with pytest.raises(HTTPException) as exc:
        _call(token)
    assert exc.value.status_code == 401


def test_missing_sub_raises_401():
    token = jwt.encode(
        {
            "aud": config.SUPABASE_JWT_AUD,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc:
        _call(token)
    assert exc.value.status_code == 401
