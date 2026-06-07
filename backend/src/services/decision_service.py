"""Transaction routing decisions (APPROVE / APPROVE_WITH_REVIEW / DECLINE).

Wires POST /api/v1/transactions end to end:
    validate body
      -> merchant blacklist short-circuit (DECLINE, scorer skipped)
      -> build card_history from prior `transactions` rows
      -> in-process score_transaction()
      -> map score -> decision via feature_schema thresholds
      -> persist transactions (+ fraud_scores, + score_reasons if explain)
      -> return score + decision

The scoring call is IN-PROCESS (not over HTTP) and is made BEFORE any DB write,
so a model failure (HTTPException 503/500 from score_transaction) persists nothing.
"""

from __future__ import annotations

import statistics
import uuid
from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.fraud_score import FraudScore
from src.db.models.score_reason import ScoreReason
from src.db.models.transaction import Transaction
from src.schemas.score_reason import ScoreReasonRead
from src.schemas.transaction import TransactionRead
from src.schemas.transaction_ingest import (
    TransactionDecisionResponse,
    TransactionIngestRequest,
)
from src.services.scoring_service import get_feature_schema, score_transaction
from src.services.watchlist_service import is_merchant_blacklisted

# Decision labels — match the scoring contract / feature_schema decision_policy.
APPROVE = "APPROVE"
APPROVE_WITH_REVIEW = "APPROVE_WITH_REVIEW"
DECLINE = "DECLINE"


# =============================================================================
# READ
# =============================================================================

async def list_transactions(db: Session, limit: int = 50) -> list[dict[str, Any]]:
    """Most recent transactions, newest first, with latest fraud score attached."""
    rows = db.execute(
        select(Transaction).order_by(Transaction.created_at.desc()).limit(limit)
    ).scalars().all()
    latest_scores = _latest_scores_by_txn(db, [r.id for r in rows])
    return [_serialize_list_item(r, latest_scores.get(r.id)) for r in rows]


async def get_transaction(db: Session, transaction_id: uuid.UUID) -> dict[str, Any]:
    """Single transaction with latest score, SHAP reasons, and feature snapshot."""
    txn = db.get(Transaction, transaction_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    fraud_score = db.execute(
        select(FraudScore)
        .where(FraudScore.transaction_id == transaction_id)
        .order_by(FraudScore.scored_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    reasons: list[ScoreReason] = []
    if fraud_score is not None:
        reasons = db.execute(
            select(ScoreReason).where(ScoreReason.score_id == fraud_score.id)
        ).scalars().all()

    return _serialize_detail(txn, fraud_score, reasons)


def _latest_scores_by_txn(
    db: Session,
    txn_ids: list[uuid.UUID],
) -> dict[uuid.UUID, FraudScore]:
    if not txn_ids:
        return {}

    rows = db.execute(
        select(FraudScore)
        .where(FraudScore.transaction_id.in_(txn_ids))
        .order_by(FraudScore.transaction_id, FraudScore.scored_at.desc())
    ).scalars().all()

    latest: dict[uuid.UUID, FraudScore] = {}
    for row in rows:
        if row.transaction_id not in latest:
            latest[row.transaction_id] = row
    return latest


def _serialize_list_item(
    txn: Transaction,
    fraud_score: FraudScore | None,
) -> dict[str, Any]:
    data = TransactionRead.model_validate(txn).model_dump(mode="json")
    if fraud_score is not None:
        data["score"] = float(fraud_score.score)
        data["model_version"] = fraud_score.model_version
    else:
        data["score"] = None
        data["model_version"] = None
    return data


def _serialize_detail(
    txn: Transaction,
    fraud_score: FraudScore | None,
    reasons: list[ScoreReason],
) -> dict[str, Any]:
    data = _serialize_list_item(txn, fraud_score)
    data["reasons"] = [
        ScoreReasonRead.model_validate(r).model_dump(mode="json") for r in reasons
    ]
    data["features"] = (
        fraud_score.features_snapshot if fraud_score is not None else None
    )
    return data


# =============================================================================
# INGEST (write path)
# =============================================================================

async def ingest(
    db: Session,
    payload: TransactionIngestRequest,
    explain: bool = False,
) -> TransactionDecisionResponse:
    # 1. Merchant blacklist short-circuit — DECLINE without scoring.
    if is_merchant_blacklisted(db, payload.merchant_id):
        txn = _build_transaction(payload, decision=DECLINE, reason_code="MERCHANT_BLACKLISTED")
        db.add(txn)
        db.flush()
        transaction_id = txn.id  # capture before commit expires the attribute
        db.commit()
        return TransactionDecisionResponse(
            transaction_id=transaction_id,
            decision=DECLINE,
            score=None,
            reason="merchant_blacklisted",
        )

    # 2. Build per-card history from prior transactions (cold-start fallback).
    card_history = _build_card_history(db, payload)

    # 3. Score in-process. Raises HTTPException(503/500) — before any DB write.
    result = await score_transaction(
        transaction=payload.scoring_transaction(),
        card_history=card_history,
        explain=explain,
    )
    score: float = result["score"]
    model_name: str = result["model_name"]
    contributions = result.get("contributions")

    # 4. Map score -> decision using schema thresholds (never hardcoded).
    thresholds = (await get_feature_schema())["thresholds"]
    decision = _map_decision(score, thresholds)

    # 5. Persist transaction + fraud_score (+ score_reasons when explaining).
    txn = _build_transaction(payload, decision=decision, reason_code=None)
    db.add(txn)
    db.flush()  # populate txn.id for the FK
    transaction_id = txn.id  # capture before commit expires the attribute

    fraud_score = FraudScore(
        transaction_id=txn.id,
        score=Decimal(str(score)),
        model_version=model_name,
        features_snapshot=None,
        is_rescore=False,
    )
    db.add(fraud_score)

    if explain and contributions:
        db.flush()  # populate fraud_score.id for the FK
        for c in contributions:
            db.add(
                ScoreReason(
                    score_id=fraud_score.id,
                    feature=c["feature"],
                    # DB CHECK constraint score_reasons_direction_check
                    # restricts direction to {'HIGH','LOW'}. Positive SHAP
                    # pushes score HIGHer (more fraud-like).
                    direction="HIGH" if c["shap_value"] > 0 else "LOW",
                    contribution=Decimal(str(c["shap_value"])),
                )
            )

    db.commit()

    return TransactionDecisionResponse(
        transaction_id=transaction_id,
        decision=decision,
        score=score,
        model_name=model_name,
        contributions=contributions if explain else None,
    )


# =============================================================================
# HELPERS
# =============================================================================

def _map_decision(score: float, thresholds: dict) -> str:
    """APPROVE < approve_below <= APPROVE_WITH_REVIEW < decline_from <= DECLINE."""
    if score < thresholds["approve_below"]:
        return APPROVE
    if score >= thresholds["decline_from"]:
        return DECLINE
    return APPROVE_WITH_REVIEW


def _build_card_history(db: Session, payload: TransactionIngestRequest) -> dict:
    """
    Aggregate prior `transactions` rows for this card (ts strictly before the
    incoming txn) into the shape the feature builder expects. Empty history =>
    cold-start defaults (txn_count=0, mean=this amount, std=1.0, last_ts=None).
    """
    rows = db.execute(
        select(Transaction.enriched_amount_usd, Transaction.ts)
        .where(
            Transaction.card_id == payload.card_id,
            Transaction.ts < payload.timestamp,
        )
        .order_by(Transaction.ts)
    ).all()

    amounts = [float(r.enriched_amount_usd) for r in rows if r.enriched_amount_usd is not None]
    timestamps = [r.ts.timestamp() for r in rows if r.ts is not None]

    if amounts:
        mean_amt = statistics.mean(amounts)
        std_amt = statistics.stdev(amounts) if len(amounts) > 1 else 1.0
    else:
        mean_amt = float(payload.enriched_amount_usd)
        std_amt = 1.0

    return {
        "txn_count": len(rows),
        "mean_amt": mean_amt,
        "std_amt": std_amt if std_amt > 0 else 1.0,
        "last_ts": timestamps[-1] if timestamps else None,
        "current_ts": payload.timestamp.timestamp(),
        "recent_timestamps": timestamps,
    }


def _build_transaction(
    payload: TransactionIngestRequest,
    decision: str,
    reason_code: str | None,
) -> Transaction:
    """Map the ingest body onto a Transaction row (scorer-only fields dropped)."""
    if payload.transaction_amount is not None:
        amount = payload.transaction_amount
        currency = payload.transaction_currency or "KES"
    else:
        # No original-currency amount supplied — persist the USD-enriched amount.
        amount = Decimal(str(payload.enriched_amount_usd))
        currency = payload.transaction_currency or "USD"

    return Transaction(
        merchant_id=payload.merchant_id,
        transaction_amount=amount,
        transaction_currency=currency,
        ts=payload.timestamp,
        card_id=payload.card_id,
        card_type=payload.card_type.value,
        channel=payload.channel.value,
        pan_entry_mode=payload.pan_entry_mode.value,
        authentication=payload.authentication.value,
        merchant_category_code=payload.merchant_category_code,
        issuing_bank_country=payload.issuing_bank_country,
        enriched_amount_usd=Decimal(str(payload.enriched_amount_usd)),
        transaction_city=payload.transaction_city,
        terminal_id=payload.terminal_id,
        user_ip=payload.user_ip,
        # Now persisted (previously body-only scorer fields).
        transaction_type=payload.transaction_type.value,
        transaction_country=payload.transaction_country,
        decision=decision,
        reason_code=reason_code,
        # is_fraud deliberately left NULL — it is a ground-truth label set later
        # by review/backfill, never by the scoring path.
    )
