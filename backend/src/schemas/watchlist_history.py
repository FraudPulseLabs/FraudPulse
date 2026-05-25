from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WatchlistHistoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    watchlist_id: uuid.UUID | None = None
    entity_type: str
    entity_id: str
    action: str
    reason: str | None = None
    actor: str
    created_at: datetime
