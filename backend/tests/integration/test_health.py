from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from src.db import session as db_session
from src.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200

    body = r.json()
    assert body["status"] == "Running"
    assert "timestamp" in body


class _StubEngine:
    """Minimal stand-in for the SQLAlchemy engine used by /health/db."""

    def __init__(self, error: Exception | None = None):
        self.error = error
        self.executed: list[str] = []

    @contextmanager
    def connect(self):
        if self.error:
            raise self.error
        yield self

    def execute(self, statement):
        self.executed.append(str(statement))


@pytest.fixture
def stub_engine(monkeypatch):
    def _apply(engine):
        monkeypatch.setattr(db_session, "engine", engine)
        return engine

    return _apply


def test_health_db_ok(stub_engine):
    engine = stub_engine(_StubEngine())

    r = client.get("/health/db")

    assert r.status_code == 200
    assert r.json()["database"] == "ok"
    assert engine.executed == ["SELECT 1"]


def test_health_db_reports_unreachable_database(stub_engine):
    stub_engine(_StubEngine(error=OperationalError("SELECT 1", {}, Exception("no route"))))

    r = client.get("/health/db")

    assert r.status_code == 503
    assert r.json()["database"] == "unreachable"


def test_health_db_reports_missing_configuration(stub_engine):
    stub_engine(None)

    r = client.get("/health/db")

    assert r.status_code == 503
    assert r.json()["database"] == "not_configured"


def test_health_db_body_matches_uptime_keyword(stub_engine):
    """The UptimeRobot keyword monitor matches on the raw response text."""
    stub_engine(_StubEngine())

    r = client.get("/health/db")

    assert '"database":"ok"' in r.text
