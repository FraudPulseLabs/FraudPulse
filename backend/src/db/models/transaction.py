#src\db\models\transaction.py
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.db.models.base import Base


class Transaction(Base):
    """Maps to `public.transactions` (Supabase). Columns mirror the live schema."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # --- Core ---
    transaction_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    transaction_currency: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'KES'")
    )
    merchant_id: Mapped[str] = mapped_column(Text, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user_ip: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_info: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    lifecycle_status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default=text("'AUTHORIZED'")
    )
    is_simulated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    is_manually_created: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    annotation: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # --- Payment / card metadata ---
    billing_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(20), nullable=True)
    card_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    card_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cardholder_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    card_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    card_entry_mode: Mapped[str | None] = mapped_column(String(30), nullable=True)
    merchant_category_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    issuing_bank_country: Mapped[str | None] = mapped_column(Text, nullable=True)
    transaction_city: Mapped[str | None] = mapped_column(Text, nullable=True)
    enriched_amount_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    pan_entry_mode: Mapped[str | None] = mapped_column(Text, nullable=True)
    terminal_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    authentication: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Data-science alignment (added 2026-05-31) ---
    # transaction_type / transaction_country: scorer fields, now persisted
    # (previously body-only) for full feature parity in re-training/analytics.
    transaction_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    transaction_country: Mapped[str | None] = mapped_column(Text, nullable=True)
    # is_fraud: GROUND-TRUTH label, NOT the live decision. Never written by the
    # ingest/scoring path; populated later by review/chargeback backfill.
    is_fraud: Mapped[bool | None] = mapped_column(Boolean, nullable=True)