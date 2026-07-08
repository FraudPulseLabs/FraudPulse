"""Unit tests for alert_service CRUD and query helpers."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.db.models.alert_model import Alert
from src.schemas.alert_schemas import AlertReason, AlertSeverity
from src.services import alert_service


def _make_alert(
    *,
    alert_id: uuid.UUID | None = None,
    transaction_id: uuid.UUID | None = None,
    reason: str = AlertReason.FRAUD_REVIEW_REQUIRED.value,
    severity: str = AlertSeverity.MEDIUM.value,
) -> Alert:
    alert = Alert(
        transaction_id=transaction_id or uuid.uuid4(),
        reason=reason,
        severity=severity,
    )
    alert.id = alert_id or uuid.uuid4()
    alert.created_at = datetime(2026, 6, 1, tzinfo=timezone.utc)
    return alert


def _db_execute_returns(rows: list[Alert]) -> MagicMock:
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = rows
    return db


class TestCreateAlert:
    def test_persists_alert_with_mapped_severity(self):
        db = MagicMock()
        txn_id = uuid.uuid4()

        alert = alert_service.create_alert(
            db=db,
            transaction_id=txn_id,
            reason=AlertReason.FRAUD_SCORE_DECLINE,
        )

        db.add.assert_called_once()
        db.flush.assert_called_once()
        added: Alert = db.add.call_args.args[0]
        assert added.transaction_id == txn_id
        assert added.reason == AlertReason.FRAUD_SCORE_DECLINE.value
        assert added.severity == AlertSeverity.HIGH.value
        assert alert is added

    def test_merchant_blacklisted_maps_to_high_severity(self):
        db = MagicMock()
        alert = alert_service.create_alert(
            db=db,
            transaction_id=uuid.uuid4(),
            reason=AlertReason.MERCHANT_BLACKLISTED,
        )
        assert alert.severity == AlertSeverity.HIGH.value


class TestGetAlerts:
    def test_returns_all_alerts_when_unfiltered(self):
        rows = [_make_alert(), _make_alert()]
        db = _db_execute_returns(rows)

        result = asyncio.run(alert_service.get_alerts(db=db))

        assert result == rows

    def test_filters_by_reason(self):
        row = _make_alert(reason=AlertReason.FRAUD_SCORE_DECLINE.value)
        db = _db_execute_returns([row])

        result = asyncio.run(
            alert_service.get_alerts(db=db, reason=AlertReason.FRAUD_SCORE_DECLINE)
        )

        assert result == [row]

    def test_filters_by_severity(self):
        row = _make_alert(severity=AlertSeverity.HIGH.value)
        db = _db_execute_returns([row])

        result = asyncio.run(
            alert_service.get_alerts(db=db, severity=AlertSeverity.HIGH)
        )

        assert result == [row]

    def test_filters_by_transaction_id(self):
        txn_id = uuid.uuid4()
        row = _make_alert(transaction_id=txn_id)
        db = _db_execute_returns([row])

        result = asyncio.run(
            alert_service.get_alerts(db=db, transaction_id=txn_id)
        )

        assert result == [row]


class TestGetAlert:
    def test_returns_alert_when_found(self):
        alert = _make_alert()
        db = MagicMock()
        db.get.return_value = alert

        result = asyncio.run(alert_service.get_alert(db=db, alert_id=alert.id))

        assert result is alert

    def test_raises_404_when_missing(self):
        db = MagicMock()
        db.get.return_value = None

        with pytest.raises(HTTPException) as exc:
            asyncio.run(alert_service.get_alert(db=db, alert_id=uuid.uuid4()))

        assert exc.value.status_code == 404
