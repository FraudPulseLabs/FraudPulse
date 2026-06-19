#backend\src\schemas\alert_schemas.py
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class AlertReason(str, Enum):
    FRAUD_REVIEW_REQUIRED = "FRAUD_REVIEW_REQUIRED"
    FRAUD_SCORE_DECLINE = "FRAUD_SCORE_DECLINE"
    MERCHANT_BLACKLISTED = "MERCHANT_BLACKLISTED"


class AlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    reason: AlertReason
    severity: AlertSeverity
    created_at: datetime


class AlertResponse(BaseModel):
    success: bool
    message: str
    data: AlertRead


class AlertListResponse(BaseModel):
    success: bool
    message: str
    data: list[AlertRead]