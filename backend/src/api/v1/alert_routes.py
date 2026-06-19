# src/api/v1/alerts.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.alert_schemas import (
    AlertListResponse,
    AlertReason,
    AlertResponse,
    AlertSeverity,
)
from src.services.alert_service import get_alert, get_alerts

router = APIRouter(tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    reason: AlertReason | None = None,
    severity: AlertSeverity | None = None,
    transaction_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> AlertListResponse:
    alerts = await get_alerts(
        db=db,
        reason=reason,
        severity=severity,
        transaction_id=transaction_id,
    )

    return AlertListResponse(
        success=True,
        message="Alerts retrieved successfully",
        data=alerts,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert_by_id(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> AlertResponse:
    alert = await get_alert(db=db, alert_id=alert_id)

    return AlertResponse(
        success=True,
        message="Alert retrieved successfully",
        data=alert,
    )