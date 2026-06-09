"""Route-level auth checks: protected routes reject anonymous calls; /demo stays open.

No valid token is minted here (that needs Supabase keys), so we only assert the
gate fires — auth is evaluated before any DB/service code runs.
"""

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_protected_route_requires_auth():
    r = client.get("/api/v1/transactions")
    assert r.status_code == 401


def test_auth_me_requires_auth():
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_demo_route_is_public():
    r = client.get("/api/v1/demo/transactions")
    # Public route: never an auth rejection (may be 200 or 503 if artifact absent).
    assert r.status_code not in (401, 403)
