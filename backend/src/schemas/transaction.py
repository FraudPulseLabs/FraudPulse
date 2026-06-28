from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_amount: Decimal
    transaction_currency: str
    merchant_id: str
    ts: datetime
    user_ip: str | None = None
    device_info: dict[str, Any] | None = None
    decision: str | None = None
    lifecycle_status: str
    is_simulated: bool
    is_manually_created: bool
    annotation: str | None = None
    created_at: datetime
    billing_amount: Decimal | None = None
    channel: str | None = None
    card_id: str | None = None
    card_type: str | None = None
    cardholder_present: bool | None = None
    card_present: bool | None = None
    card_entry_mode: str | None = None
    merchant_category_code: str | None = None
    issuing_bank_country: str | None = None
    transaction_city: str | None = None
    enriched_amount_usd: Decimal | None = None
    pan_entry_mode: str | None = None
    terminal_id: str | None = None
    authentication: str | None = None
    reason_code: str | None = None
    transaction_type: str | None = None
    transaction_country: str | None = None
    is_fraud: bool | None = None


class TransactionCreate(BaseModel):
    # Required (NOT NULL with no DB default)
    transaction_amount: Decimal
    merchant_id: str
    ts: datetime

    # Defaulted in the DB — optional on create
    transaction_currency: str = "KES"
    lifecycle_status: str = "AUTHORIZED"
    is_simulated: bool = False
    is_manually_created: bool = False

    # Nullable
    user_ip: str | None = None
    device_info: dict[str, Any] | None = None
    decision: str | None = None
    annotation: str | None = None
    billing_amount: Decimal | None = None
    channel: str | None = None
    card_id: str | None = None
    card_type: str | None = None
    cardholder_present: bool | None = None
    card_present: bool | None = None
    card_entry_mode: str | None = None
    merchant_category_code: str | None = None
    issuing_bank_country: str | None = None
    transaction_city: str | None = None
    enriched_amount_usd: Decimal | None = None
    pan_entry_mode: str | None = None
    terminal_id: str | None = None
    authentication: str | None = None
    reason_code: str | None = None
    transaction_type: str | None = None
    transaction_country: str | None = None
    # is_fraud: ground-truth label, populated by review/backfill — not at create.
    is_fraud: bool | None = None
