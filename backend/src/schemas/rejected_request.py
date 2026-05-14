from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RejectedRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    payload: dict[str, Any] | None = None
    errors: Any
    source_ip: str | None = None
    submitted_at: datetime
