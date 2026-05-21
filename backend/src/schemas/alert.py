from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    case_id: uuid.UUID | None = None
    reason: str
    severity: str
    status: str
    acknowledged_by: uuid.UUID | None = None
    acknowledged_at: datetime | None = None
    resolved_by: uuid.UUID | None = None
    resolved_at: datetime | None = None
    resolution_note: str | None = None
    created_at: datetime
