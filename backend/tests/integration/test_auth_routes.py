"""Route-level auth checks: protected routes reject anonymous calls; /demo stays open.

No valid token is minted here (that needs Supabase keys), so we only assert the
gate fires — auth is evaluated before any DB/service code runs.
"""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_protected_route_requires_auth():
    r = client.get("/api/v1/transactions")
    assert r.status_code == 401


def test_auth_me_requires_auth():
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401


def test_alerts_route_requires_auth():
    r = client.get("/api/v1/alerts")
    assert r.status_code == 401


def test_cases_route_requires_auth():
    r = client.get("/api/v1/cases")
    assert r.status_code == 401


def test_watchlist_route_requires_auth():
    r = client.get("/api/v1/watchlist")
    assert r.status_code == 401


def test_demo_route_is_public():
    r = client.get("/api/v1/demo/transactions")
    # Public route: never an auth rejection (may be 200 or 503 if artifact absent).
    assert r.status_code not in (401, 403)


def test_demo_score_is_public(client):
    payload = {
        "card_id": "c_fa566bcc55a9",
        "merchant_id": "m_47d74a000558",
        "timestamp": "2025-01-25T19:51:34",
        "enriched_amount_usd": 0.02,
        "issuing_bank_country": "KEN",
        "transaction_country": "KEN",
        "cvv2_result": "NOT_APPLICABLE",
        "avs_result": "NOT_PERFORMED",
        "pan_entry_mode": "CONTACTLESS",
        "authentication": "PIN",
        "card_type": "Credit",
        "channel": "POS",
        "transaction_type": "purchase",
        "merchant_category_code": "5999",
        "transaction_amount": 2.0,
        "transaction_currency": "KES",
        "transaction_city": "Nairobi",
    }
    with patch(
        "src.api.v1.demo.score_transaction",
        new=AsyncMock(
            return_value={
                "score": 0.12,
                "model_name": "calibrated_lightgbm_version2",
                "contributions": [{"feature": "txn_count_1h", "value": 0.0, "shap_value": 0.1}],
            }
        ),
    ), patch(
        "src.api.v1.demo.get_feature_schema",
        new=AsyncMock(return_value={"thresholds": {"approve_below": 0.1, "decline_from": 0.8}}),
    ):
        r = client.post("/api/v1/demo/score?explain=true", json=payload)

    assert r.status_code == 200
    body = r.json()
    assert body["decision"] in {"APPROVE", "APPROVE_WITH_REVIEW", "DECLINE"}
    assert body["score"] == 0.12
