from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ScoreReasonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    score_id: uuid.UUID
    feature: str
    direction: str
    contribution: Decimal
