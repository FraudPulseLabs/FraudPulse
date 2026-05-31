# src/db/models/watchlist_model.py

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.models.base import Base


class Watchlist(Base):
    __tablename__ = "watchlist"
    __table_args__ = (
        UniqueConstraint(
            "watchlist_entity_type", "watchlist_entity_id", name="uq_watchlist_entity"
        ),
        CheckConstraint(
            "risk_severity = ANY(ARRAY['LOW', 'MEDIUM', 'HIGH'])",
            name="watchlist_risk_severity_check",
        ),
        CheckConstraint(
            "watchlist_entity_type = ANY(ARRAY['TRANSACTION', 'USER', 'MERCHANT'])",
            name="watchlist_watchlist_entity_type_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    watchlist_entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    watchlist_entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    watchlist_reason: Mapped[str] = mapped_column(Text, nullable=False)
    risk_severity: Mapped[str] = mapped_column(Text, nullable=False)
    is_blacklist: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    history: Mapped[list[WatchlistHistory]] = relationship(
        "WatchlistHistory", back_populates="watchlist", cascade="all, delete"
    )


class WatchlistHistory(Base):
    __tablename__ = "watchlist_history"
    __table_args__ = (
        CheckConstraint(
            "action = ANY(ARRAY['ADDED', 'UPDATED', 'REMOVED', 'EXPIRED'])",
            name="watchlist_history_action_check",
        ),
        CheckConstraint(
            "watchlist_entity_type = ANY(ARRAY['TRANSACTION', 'USER', 'MERCHANT'])",
            name="watchlist_history_entity_type_check",
        ),
        CheckConstraint(
            "risk_severity = ANY(ARRAY['LOW', 'MEDIUM', 'HIGH'])",
            name="watchlist_history_risk_severity_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("watchlist.id", ondelete="CASCADE"),
        nullable=False,
    )
    watchlist_entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    watchlist_entity_id: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    watchlist_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_severity: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_blacklist: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    watchlist: Mapped[Watchlist] = relationship("Watchlist", back_populates="history")
