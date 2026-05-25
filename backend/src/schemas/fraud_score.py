from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class FraudScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_id: uuid.UUID
    score: Decimal
    model_version: str
    features_snapshot: dict[str, Any] | None = None
    scored_at: datetime
    is_rescore: bool
