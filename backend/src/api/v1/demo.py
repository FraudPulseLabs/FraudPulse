"""
GET /api/v1/demo/transactions
POST /api/v1/demo/score

Public endpoints for the frontend Model Validation page. Scoring runs the
calibrated model with cold-start card history (no DB persistence) so analysts
can evaluate held-out rows without polluting production data or tripping
watchlist side effects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from src.core.rate_limit import LIMIT_DEMO, limiter

from src.schemas.transaction_ingest import TransactionIngestRequest
from src.services.decision_service import _map_decision
from src.services.scoring_service import get_feature_schema, score_transaction

router = APIRouter()

_DEMO_PATH = (
    Path(__file__).resolve().parents[3]
    / "ml"
    / "data"
    / "demo"
    / "demo_transactions.json"
)


def _cold_start_card_history(payload: TransactionIngestRequest) -> dict[str, Any]:
    """Demo scoring uses no prior card history — matches held-out evaluation."""
    return {
        "txn_count": 0,
        "mean_amt": float(payload.enriched_amount_usd),
        "std_amt": 1.0,
        "last_ts": None,
        "current_ts": payload.timestamp.timestamp(),
        "recent_timestamps": [],
    }


@router.get("/transactions")
@limiter.limit(LIMIT_DEMO)
async def list_demo_transactions(request: Request) -> list[dict[str, Any]]:
    if not _DEMO_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Demo artifact missing. Run "
                "`python -m scripts.seed_demo_transactions` from the backend dir."
            ),
        )
    return json.loads(_DEMO_PATH.read_text())


@router.post("/score")
@limiter.limit(LIMIT_DEMO)
async def score_demo_transaction(
    request: Request,
    payload: TransactionIngestRequest,
    explain: bool = Query(default=False),
) -> dict[str, Any]:
    """Score a demo row through the model without persisting to the database."""
    result = await score_transaction(
        transaction=payload.scoring_transaction(),
        card_history=_cold_start_card_history(payload),
        explain=explain,
    )
    thresholds = (await get_feature_schema())["thresholds"]
    decision = _map_decision(result["score"], thresholds)

    return {
        "decision": decision.value,
        "score": result["score"],
        "model_name": result["model_name"],
        "contributions": result.get("contributions") if explain else None,
    }
