from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_type: str
    entity_type: str | None = None
    entity_id: str | None = None
    actor_id: str | None = None
    details: dict[str, Any] | None = None
    created_at: datetime
