from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.services import scoring_service

router = APIRouter()


@router.post("")
async def score(body: dict[str, Any]) -> dict[str, Any]:
    return await scoring_service.score_transaction(body)
