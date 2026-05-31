"""
Request / response models for POST /api/v1/transactions.

The ingest body is a single flat authorisation-style message. It carries:
  * the 14 fields the fraud scorer needs (see scoring_schemas.TransactionPayload),
  * merchant_id — used for the blacklist check and persisted (NOT NULL column);
    the scorer's transaction object has no merchant_id, hence it lives here,
  * optional persistence-only fields (amount/currency in the original currency,
    plus a few nullable columns) that the scorer does not use.

The 4 scorer-only fields (transaction_country, cvv2_result, avs_result,
transaction_type) have NO column in the live `transactions` table — they ride
in this body purely so the scorer can build its features.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from src.schemas.scoring_schemas import (
    AuthenticationMethod,
    AvsResult,
    CardType,
    Channel,
    CvvResult,
    FeatureContribution,
    PanEntryMode,
    TransactionType,
)


class TransactionIngestRequest(BaseModel):
    """Flat POST /transactions body: scorer fields + merchant_id + persistence."""

    # --- identity / blacklist key ---
    card_id: str
    merchant_id: str

    # --- scorer fields (mirror scoring_schemas.TransactionPayload) ---
    timestamp: datetime
    enriched_amount_usd: float = Field(..., gt=0)
    issuing_bank_country: str
    transaction_country: str
    cvv2_result: CvvResult
    avs_result: AvsResult
    pan_entry_mode: PanEntryMode
    authentication: AuthenticationMethod
    card_type: CardType
    channel: Channel
    transaction_type: TransactionType
    merchant_category_code: str

    # --- persistence-only (optional) ---
    # original-currency amount for the transactions row. transaction_amount is
    # NOT NULL in the DB; if omitted we persist enriched_amount_usd as "USD".
    transaction_amount: Decimal | None = Field(default=None, gt=0)
    transaction_currency: str | None = None
    transaction_city: str | None = None
    terminal_id: str | None = None
    user_ip: str | None = None

    def scoring_transaction(self) -> dict:
        """The 14-field dict the scorer/feature-builder expects (enum -> str)."""
        return {
            "card_id": self.card_id,
            "timestamp": self.timestamp,
            "enriched_amount_usd": float(self.enriched_amount_usd),
            "issuing_bank_country": self.issuing_bank_country,
            "transaction_country": self.transaction_country,
            "cvv2_result": self.cvv2_result.value,
            "avs_result": self.avs_result.value,
            "pan_entry_mode": self.pan_entry_mode.value,
            "authentication": self.authentication.value,
            "card_type": self.card_type.value,
            "channel": self.channel.value,
            "transaction_type": self.transaction_type.value,
            "merchant_category_code": self.merchant_category_code,
        }


class TransactionDecisionResponse(BaseModel):
    """Returned by POST /transactions."""

    transaction_id: uuid.UUID
    decision: str  # APPROVE | APPROVE_WITH_REVIEW | DECLINE
    score: float | None = None  # None when the scorer was skipped (blacklist)
    model_name: str | None = None
    reason: str | None = None  # e.g. "merchant_blacklisted"
    contributions: list[FeatureContribution] | None = None  # only when explain=True
