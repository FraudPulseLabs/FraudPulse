# src/schemas/scoring_schemas.py

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# ENUMS
# =============================================================================

class CardType(StrEnum):
    DEBIT    = "Debit"
    CREDIT   = "Credit"
    PREPAID  = "Prepaid"


class Channel(StrEnum):
    ATM       = "ATM"
    ECOMMERCE = "ECOMMERCE"
    POS       = "POS"


class TransactionType(StrEnum):
    PURCHASE   = "purchase"
    WITHDRAWAL = "withdrawal"


class CvvResult(StrEnum):
    MATCH          = "MATCH"
    NOT_PROVIDED   = "NOT_PROVIDED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class AvsResult(StrEnum):
    FULL_MATCH    = "FULL_MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    NOT_PERFORMED = "NOT_PERFORMED"


class PanEntryMode(StrEnum):
    CHIP        = "CHIP"
    CONTACTLESS = "CONTACTLESS"
    ONLINE      = "ONLINE"
    MAGSTRIPE   = "MAGSTRIPE"


class AuthenticationMethod(StrEnum):
    BIOMETRICS = "BIOMETRICS"
    OTP        = "OTP"
    PIN        = "PIN"
    CVV2       = "CVV2"
    NONE       = "NONE"


# =============================================================================
# REQUEST — transaction fields + card history (from card store)
# =============================================================================

class TransactionPayload(BaseModel):
    """Raw transaction fields from the txn authorisation message."""
    card_id:                str
    timestamp:              datetime
    enriched_amount_usd:    float = Field(..., gt=0)
    issuing_bank_country:   str
    transaction_country:    str
    cvv2_result:            CvvResult
    avs_result:             AvsResult
    pan_entry_mode:         PanEntryMode
    authentication:         AuthenticationMethod
    card_type:              CardType
    channel:                Channel
    transaction_type:       TransactionType
    merchant_category_code: str


class CardHistoryPayload(BaseModel):
    """
    Per-card aggregates queried from the card history store before scoring.
    txn_count = 0 signals a cold-start card (first transaction ever).
    """
    txn_count:         int          = Field(..., ge=0)
    mean_amt:          float        = Field(..., ge=0)
    std_amt:           float        = Field(..., ge=0)
    last_ts:           float | None = None
    current_ts:        float
    recent_timestamps: list[float]  = Field(default_factory=list)


class ScoringRequest(BaseModel):
    transaction:  TransactionPayload
    card_history: CardHistoryPayload


# =============================================================================
# RESPONSE
# =============================================================================

class FeatureContribution(BaseModel):
    """
    SHAP value for a single feature on this transaction.

    shap_value > 0  → pushed the score higher (toward fraud)
    shap_value < 0  → pushed the score lower (toward legitimate)
    abs(shap_value) → magnitude of influence
    """
    feature:    str
    value:      float   # the actual feature value fed to the model
    shap_value: float   # contribution to the log-odds of fraud


class ScoringResponse(BaseModel):
    """
    Returned by POST /score.
    Decision logic (APPROVE / REVIEW / DECLINE) is applied by the caller
    using the thresholds from GET /schema.
    """
    model_config = ConfigDict(protected_namespaces=())

    score:         float = Field(..., ge=0, le=1)
    model_name:    str
    contributions: list[FeatureContribution] | None = None   # None if explain=False