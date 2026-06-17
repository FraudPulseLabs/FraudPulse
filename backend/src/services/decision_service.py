#backend\src\services\decision_service.py
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

from src.schemas.alert_schemas import AlertReason
from src.schemas.decision_schemas import Decision
from src.schemas.transaction import TransactionRead
from src.schemas.transaction_ingest import (
    TransactionDecisionResponse,
    TransactionIngestRequest,
)

from src.services.event_emitter import event_emitter
from src.services.scoring_service import get_feature_schema, score_transaction
from src.services.watchlist_service import is_merchant_blacklisted


# =============================================================================
# READ
# =============================================================================

async def list_transactions(db: Session, limit: int = 50) -> list[dict]:
    """Most recent transactions, newest first."""
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
# INGEST
# =============================================================================

async def ingest(
    db: Session,
    payload: TransactionIngestRequest,
    explain: bool = False,
) -> TransactionDecisionResponse:

    # 1. BLACKLIST SHORT CIRCUIT
    if is_merchant_blacklisted(db, payload.merchant_id):
        txn = _build_transaction(
            payload,
            decision=Decision.DECLINE,
            reason_code="MERCHANT_BLACKLISTED",
        )

        db.add(txn)
        db.flush()

        transaction_id = txn.id
        db.commit()

        return TransactionDecisionResponse(
            transaction_id=transaction_id,
            decision=Decision.DECLINE.value,
            score=None,
            reason="merchant_blacklisted",
        )

    # 2. CARD HISTORY
    card_history = _build_card_history(db, payload)

    # 3. SCORE
    result = await score_transaction(
        transaction=payload.scoring_transaction(),
        card_history=card_history,
        explain=explain,
    )

    score: float = result["score"]
    model_name: str = result["model_name"]
    contributions = result.get("contributions")

    # 4. DECISION
    thresholds = (await get_feature_schema())["thresholds"]
    decision = _map_decision(score, thresholds)

    # 5. PERSIST TRANSACTION
    txn = _build_transaction(
        payload,
        decision=decision,
        reason_code=None,
    )

    db.add(txn)
    db.flush()
    transaction_id = txn.id

    fraud_score = FraudScore(
        transaction_id=txn.id,
        score=Decimal(str(score)),
        model_version=model_name,
        features_snapshot=None,
        is_rescore=False,
    )
    db.add(fraud_score)

    # 6. ALERTS (via event emitter)

    if decision == Decision.APPROVE_WITH_REVIEW:
        event_emitter.emit(
            "fraud_review_required",
            db=db,
            transaction_id=txn.id,
        )

    elif decision == Decision.DECLINE:
        event_emitter.emit(
            "fraud_decline",
            db=db,
            transaction_id=txn.id,
        )

    # 7. EXPLANATIONS
    if explain and contributions:
        db.flush()
        for c in contributions:
            db.add(
                ScoreReason(
                    score_id=fraud_score.id,
                    feature=c["feature"],
                    direction="HIGH" if c["shap_value"] > 0 else "LOW",
                    contribution=Decimal(str(c["shap_value"])),
                )
            )

    db.commit()

    return TransactionDecisionResponse(
        transaction_id=transaction_id,
        decision=decision.value,
        score=score,
        model_name=model_name,
        contributions=contributions if explain else None,
    )


# =============================================================================
# HELPERS
# =============================================================================

def _map_decision(score: float, thresholds: dict) -> Decision:
    if score < thresholds["approve_below"]:
        return Decision.APPROVE

    if score >= thresholds["decline_from"]:
        return Decision.DECLINE

    return Decision.APPROVE_WITH_REVIEW


def _build_card_history(db: Session, payload: TransactionIngestRequest) -> dict:
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


def _build_transaction(payload, decision: Decision, reason_code: str | None):
    if payload.transaction_amount is not None:
        amount = payload.transaction_amount
        currency = payload.transaction_currency or "KES"
    else:
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
        transaction_type=payload.transaction_type.value,
        transaction_country=payload.transaction_country,
        decision=decision.value,
        reason_code=reason_code,
    )