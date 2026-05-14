from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.services import decision_service

router = APIRouter()


@router.get("")
async def list_transactions() -> list[dict[str, Any]]:
    return await decision_service.list_transactions()


@router.post("")
async def ingest_transaction(body: dict[str, Any]) -> dict[str, Any]:
    return await decision_service.decide({"transaction_id": None, **body})
