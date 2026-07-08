from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.session import get_db
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
async def get_transaction(
    transaction_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return await decision_service.get_transaction(db, transaction_id)


@router.post("", response_model=TransactionDecisionResponse)
async def ingest_transaction(
    payload: TransactionIngestRequest,
    explain: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> TransactionDecisionResponse:
    return await decision_service.ingest(db, payload, explain=explain)
