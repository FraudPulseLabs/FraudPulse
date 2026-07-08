# src/api/v1/scoring.py

from __future__ import annotations

from fastapi import APIRouter, Query

from src.schemas.scoring_schemas import ScoringRequest, ScoringResponse
from src.services.scoring_service import get_feature_schema, score_transaction

router = APIRouter(tags=["scoring"])


@router.post("/score", response_model=ScoringResponse)
async def score(
    payload: ScoringRequest,
    explain: bool = Query(default=False),
):
    return await score_transaction(
        transaction=payload.transaction.model_dump(),
        card_history=payload.card_history.model_dump(),
        explain=explain,
    )


@router.get("/schema")
async def schema():
    return await get_feature_schema()