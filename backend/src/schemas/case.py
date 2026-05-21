from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    status: str
    risk_level: str
    resolution_code: str | None = None
    assigned_to: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
