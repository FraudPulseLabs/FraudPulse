"""Shared pytest fixtures for integration and route-level tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from src.core import config
from src.main import app

TEST_JWT_SECRET = "integration-test-jwt-secret"


@pytest.fixture(autouse=True)
def _hs256_jwt_secret(monkeypatch):
    """Force HS256 verification so tests never hit Supabase JWKS."""
    monkeypatch.setattr(config, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    yield


@pytest.fixture
def auth_token() -> str:
    return jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "email": "analyst@fraudpulse.test",
            "aud": config.SUPABASE_JWT_AUD,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        TEST_JWT_SECRET,
        algorithm="HS256",
    )


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
