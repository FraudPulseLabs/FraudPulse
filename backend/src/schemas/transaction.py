from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transaction_amount: Decimal
    transaction_currency: str
    merchant_name: str
    transaction_timestamp: datetime
    customer_ip_address: str | None = None
    device_metadata: dict[str, Any] | None = None
    fraud_decision: str | None = None
    transaction_status: str
    is_simulated: bool
    is_manually_created: bool
    review_notes: str | None = None
    created_at: datetime
    billing_amount: Decimal | None = None
    billing_exchange_rate: Decimal | None = None
    transaction_channel: str | None = None
    card_reference: str | None = None
    card_type: str | None = None
    cardholder_present: bool | None = None
    card_present: bool | None = None
    card_entry_mode: str | None = None
    cvv2_result: str | None = None
    address_verification_result: str | None = None
    card_expiry: date | None = None
    merchant_category_code: str | None = None


class TransactionCreate(BaseModel):
    transaction_amount: Decimal
    transaction_currency: str
    merchant_name: str
    transaction_timestamp: datetime
    transaction_status: str
    is_simulated: bool = False
    is_manually_created: bool = False
    customer_ip_address: str | None = None
    device_metadata: dict[str, Any] | None = None
    fraud_decision: str | None = None
    review_notes: str | None = None
    billing_amount: Decimal | None = None
    billing_exchange_rate: Decimal | None = None
    transaction_channel: str | None = None
    card_reference: str | None = None
    card_type: str | None = None
    cardholder_present: bool | None = None
    card_present: bool | None = None
    card_entry_mode: str | None = None
    cvv2_result: str | None = None
    address_verification_result: str | None = None
    card_expiry: date | None = None
    merchant_category_code: str | None = None
