# src/api/v1/transactions.py
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models.fraud_score import FraudScore
from src.db.models.transaction import Transaction
from src.schemas.transaction import TransactionRead
from src.schemas.transaction_ingest import (
    TransactionDecisionResponse,
    TransactionIngestRequest,
)
from src.services import decision_service

router = APIRouter()


@router.get("")
async def list_transactions(
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return await decision_service.list_transactions(db)


@router.get("/{transaction_id}")
async def get_transaction_by_id(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    txn = db.get(Transaction, transaction_id)
    if txn is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    score_row = db.execute(
        select(FraudScore)
        .where(FraudScore.transaction_id == transaction_id)
        .order_by(FraudScore.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()

    result = TransactionRead.model_validate(txn).model_dump(mode="json")
    result["fraud_score"]   = float(score_row.score)         if score_row else None
    result["model_version"] = score_row.model_version        if score_row else None

    return result


@router.post("", response_model=TransactionDecisionResponse)
async def ingest_transaction(
    payload: TransactionIngestRequest,
    explain: bool = False,
    db: Session = Depends(get_db),
) -> TransactionDecisionResponse:
    return await decision_service.ingest(db, payload, explain=explain)