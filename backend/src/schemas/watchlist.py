from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WatchlistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    watchlist_entity_type: str
    watchlist_entity_id: str
    watchlist_reason: str
    risk_severity: str
    is_blacklist: bool
    created_by: str
    expires_at: datetime | None = None
    created_at: datetime
