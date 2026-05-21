from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.db.models.base import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    watchlist_entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    watchlist_entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    watchlist_reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_severity: Mapped[str] = mapped_column(Text, nullable=False)
    is_blacklist: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
