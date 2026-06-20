"""Integration tests for alerts, cases, and watchlist API routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.schemas.alert_schemas import AlertListResponse, AlertRead, AlertReason, AlertSeverity
from src.schemas.case_schemas import CaseNoteRead, CaseRead, CaseRiskLevel, CaseStatus
from src.schemas.watchlist_schemas import EntityType, RiskSeverity, WatchlistRead


@pytest.fixture
def sample_alert_read() -> AlertRead:
    return AlertRead(
        id=uuid.uuid4(),
        transaction_id=uuid.uuid4(),
        reason=AlertReason.FRAUD_REVIEW_REQUIRED,
        severity=AlertSeverity.MEDIUM,
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_case_read() -> CaseRead:
    return CaseRead(
        id=uuid.uuid4(),
        transaction_id=uuid.uuid4(),
        title="ATM cash-out surge",
        status=CaseStatus.OPEN,
        risk_level=CaseRiskLevel.HIGH,
        resolution_code=None,
        assigned_to=None,
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 2, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_watchlist_read() -> WatchlistRead:
    return WatchlistRead(
        id=uuid.uuid4(),
        watchlist_entity_type=EntityType.MERCHANT,
        watchlist_entity_id="merch_test_001",
        watchlist_reason="Repeated ATM withdrawals",
        risk_severity=RiskSeverity.HIGH,
        is_blacklist=True,
        created_by="analyst@fraudpulse.test",
        expires_at=None,
        created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
    )


class TestAlertRoutes:
    def test_list_alerts_requires_auth(self, client):
        response = client.get("/api/v1/alerts")
        assert response.status_code == 401

    def test_list_alerts_returns_wrapped_payload(self, client, auth_headers, sample_alert_read):
        with patch(
            "src.api.v1.alert_routes.get_alerts",
            new=AsyncMock(return_value=[sample_alert_read]),
        ):
            response = client.get("/api/v1/alerts", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert len(body["data"]) == 1
        assert body["data"][0]["reason"] == AlertReason.FRAUD_REVIEW_REQUIRED.value


class TestCaseRoutes:
    def test_list_cases_requires_auth(self, client):
        response = client.get("/api/v1/cases")
        assert response.status_code == 401

    def test_list_cases_returns_array(self, client, auth_headers, sample_case_read):
        with patch(
            "src.api.v1.cases_routes.list_cases",
            new=AsyncMock(return_value=[sample_case_read]),
        ):
            response = client.get("/api/v1/cases", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert body[0]["title"] == "ATM cash-out surge"
        assert body[0]["status"] == CaseStatus.OPEN.value

    def test_list_case_notes(self, client, auth_headers, sample_case_read):
        note = CaseNoteRead(
            id=uuid.uuid4(),
            case_id=sample_case_read.id,
            author_id="analyst@fraudpulse.test",
            body="Review in progress.",
            created_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        with patch(
            "src.api.v1.cases_routes.list_case_notes",
            return_value=[note],
        ):
            response = client.get(
                f"/api/v1/cases/{sample_case_read.id}/notes",
                headers=auth_headers,
            )

        assert response.status_code == 200
        assert response.json()[0]["body"] == "Review in progress."


class TestWatchlistRoutes:
    def test_list_watchlist_requires_auth(self, client):
        response = client.get("/api/v1/watchlist")
        assert response.status_code == 401

    def test_list_watchlist_returns_wrapped_payload(
        self, client, auth_headers, sample_watchlist_read
    ):
        with patch(
            "src.api.v1.watchlist_routes.get_watchlist_entries",
            new=AsyncMock(return_value=[sample_watchlist_read]),
        ):
            response = client.get("/api/v1/watchlist", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"][0]["watchlist_entity_id"] == "merch_test_001"

    def test_create_watchlist_entry(self, client, auth_headers, sample_watchlist_read):
        with patch(
            "src.api.v1.watchlist_routes.add_watchlist_entry",
            new=AsyncMock(return_value=sample_watchlist_read),
        ):
            response = client.post(
                "/api/v1/watchlist",
                headers=auth_headers,
                json={
                    "watchlist_entity_type": "MERCHANT",
                    "watchlist_entity_id": "merch_test_001",
                    "watchlist_reason": "Repeated ATM withdrawals",
                    "risk_severity": "HIGH",
                    "is_blacklist": True,
                    "created_by": "analyst@fraudpulse.test",
                    "expires_at": None,
                },
            )

        assert response.status_code == 201
        assert response.json()["data"]["is_blacklist"] is True
