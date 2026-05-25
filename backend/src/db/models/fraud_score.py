from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.db.models.base import Base


class FraudScore(Base):
    __tablename__ = "fraud_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transactions.id"),
        nullable=False,
        index=True,
    )
    score: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    features_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    is_rescore: Mapped[bool] = mapped_column(Boolean, nullable=False)
