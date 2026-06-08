# src/schemas/watchlist_schemas.py

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict


class EntityType(StrEnum):
    TRANSACTION = "TRANSACTION"
    USER = "USER"
    MERCHANT = "MERCHANT"


class RiskSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class HistoryAction(StrEnum):
    ADDED = "ADDED"
    UPDATED = "UPDATED"
    REMOVED = "REMOVED"
    EXPIRED = "EXPIRED"


class WatchlistCreate(BaseModel):
    watchlist_entity_type: EntityType
    watchlist_entity_id: str
    watchlist_reason: str
    risk_severity: RiskSeverity
    is_blacklist: bool
    created_by: str
    expires_at: datetime | None = None


class WatchlistUpdate(BaseModel):
    watchlist_reason: str | None = None
    risk_severity: RiskSeverity | None = None
    is_blacklist: bool | None = None
    expires_at: datetime | None = None


class WatchlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    watchlist_entity_type: EntityType
    watchlist_entity_id: str
    watchlist_reason: str
    risk_severity: RiskSeverity
    is_blacklist: bool
    created_by: str
    expires_at: datetime | None = None
    created_at: datetime


class WatchlistHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    watchlist_id: uuid.UUID
    watchlist_entity_type: EntityType
    watchlist_entity_id: str
    action: HistoryAction
    watchlist_reason: str | None = None
    risk_severity: RiskSeverity | None = None
    is_blacklist: bool | None = None
    created_by: str
    expires_at: datetime | None = None
    created_at: datetime


class WatchlistApiResponse(BaseModel):
    success: bool
    message: str
    data: Any | None = None