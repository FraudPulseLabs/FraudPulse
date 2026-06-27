"""Rate limiting on public endpoints."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from src.core.rate_limit import limiter
from src.main import app

client = TestClient(app)


def _mock_rag_answer():
    result = MagicMock()
    result.answer = "FraudPulse detects payment fraud."
    result.sources = []
    result.grounded = True
    result.refused = False
    result.latency_ms = 1.0
    result.model = "test-model"
    result.to_dict = MagicMock(return_value={})
    return result


def test_assistant_rate_limit_returns_429():
    limiter.enabled = True
    limiter.reset()

    payload = {"message": "What is FraudPulse?"}
    with patch("rag.app.rag_system.get_rag_system") as mock_get_rag:
        mock_get_rag.return_value.answer.return_value = _mock_rag_answer()

        for _ in range(10):
            r = client.post("/api/v1/assistant/chat", json=payload)
            assert r.status_code == 200

        r = client.post("/api/v1/assistant/chat", json=payload)
        assert r.status_code == 429
        assert "rate limit" in r.json()["error"].lower()

    limiter.enabled = False
    limiter.reset()


def test_protected_routes_are_not_rate_limited_by_public_limits():
    """Exhausting a public quota must not block unrelated protected routes."""
    limiter.enabled = True
    limiter.reset()

    payload = {"message": "What is FraudPulse?"}
    with patch("rag.app.rag_system.get_rag_system") as mock_get_rag:
        mock_get_rag.return_value.answer.return_value = _mock_rag_answer()
        for _ in range(11):
            client.post("/api/v1/assistant/chat", json=payload)

        r = client.get("/api/v1/transactions")
        assert r.status_code == 401

    limiter.enabled = False
    limiter.reset()
