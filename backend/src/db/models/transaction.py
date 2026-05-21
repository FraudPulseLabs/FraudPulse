from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.db.models.base import Base


class Transaction(Base):
    """Maps to `public.transactions` (Supabase)."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    transaction_amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    transaction_currency: Mapped[str] = mapped_column(Text, nullable=False)
    merchant_name: Mapped[str] = mapped_column(Text, nullable=False)
    transaction_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    customer_ip_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    fraud_decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    transaction_status: Mapped[str] = mapped_column(Text, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_manually_created: Mapped[bool] = mapped_column(Boolean, nullable=False)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    billing_amount: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    billing_exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    transaction_channel: Mapped[str | None] = mapped_column(Text, nullable=True)
    card_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    card_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    cardholder_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    card_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    card_entry_mode: Mapped[str | None] = mapped_column(Text, nullable=True)
    cvv2_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    address_verification_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    card_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    merchant_category_code: Mapped[str | None] = mapped_column(Text, nullable=True)
