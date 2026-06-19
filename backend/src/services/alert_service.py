#backend\src\services\alert_service.py
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.alert_model import Alert
from src.schemas.alert_schemas import AlertReason, AlertSeverity
from src.services.event_emitter import event_emitter


def _severity_from_reason(reason: AlertReason) -> AlertSeverity:
    mapping = {
        AlertReason.FRAUD_REVIEW_REQUIRED: AlertSeverity.MEDIUM,
        AlertReason.FRAUD_SCORE_DECLINE: AlertSeverity.HIGH,
        AlertReason.MERCHANT_BLACKLISTED: AlertSeverity.HIGH,
    }
    return mapping[reason]


def create_alert(
    db: Session,
    transaction_id: uuid.UUID,
    reason: AlertReason,
) -> Alert:
    alert = Alert(
        transaction_id=transaction_id,
        reason=reason.value,
        severity=_severity_from_reason(reason).value,
    )

    db.add(alert)
    db.flush()

    return alert


async def get_alerts(
    db: Session,
    reason: AlertReason | None = None,
    severity: AlertSeverity | None = None,
    transaction_id: uuid.UUID | None = None,
) -> list[Alert]:
    query = select(Alert)

    if reason:
        query = query.where(Alert.reason == reason.value)

    if severity:
        query = query.where(Alert.severity == severity.value)

    if transaction_id:
        query = query.where(Alert.transaction_id == transaction_id)

    rows = (
        db.execute(query.order_by(Alert.created_at.desc()))
        .scalars()
        .all()
    )

    return rows


async def get_alert(
    db: Session,
    alert_id: uuid.UUID,
) -> Alert:
    alert = db.get(Alert, alert_id)

    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert


# =============================================================================
# EVENT HANDLERS
# =============================================================================

def handle_fraud_review_required(
    db: Session,
    transaction_id: uuid.UUID,
) -> None:
    create_alert(
        db=db,
        transaction_id=transaction_id,
        reason=AlertReason.FRAUD_REVIEW_REQUIRED,
    )


def handle_fraud_decline(
    db: Session,
    transaction_id: uuid.UUID,
) -> None:
    create_alert(
        db=db,
        transaction_id=transaction_id,
        reason=AlertReason.FRAUD_SCORE_DECLINE,
    )


event_emitter.subscribe("fraud_review_required", handle_fraud_review_required)
event_emitter.subscribe("fraud_decline", handle_fraud_decline)