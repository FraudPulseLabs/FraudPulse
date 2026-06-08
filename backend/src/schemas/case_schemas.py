from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    CLOSED = "CLOSED"


class CaseRiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class CaseResolutionCode(str, Enum):
    CONFIRMED_FRAUD = "CONFIRMED_FRAUD"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    INCONCLUSIVE = "INCONCLUSIVE"


class CaseCreate(BaseModel):
    title: str
    status: CaseStatus = CaseStatus.OPEN
    risk_level: CaseRiskLevel = CaseRiskLevel.MEDIUM
    resolution_code: CaseResolutionCode | None = None
    assigned_to: uuid.UUID | None = None


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    title: str
    status: CaseStatus
    risk_level: CaseRiskLevel
    resolution_code: CaseResolutionCode | None = None
    assigned_to: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class CaseUpdate(BaseModel):
    status: CaseStatus | None = None
    risk_level: CaseRiskLevel | None = None
    resolution_code: CaseResolutionCode | None = None
    assigned_to: uuid.UUID | None = None