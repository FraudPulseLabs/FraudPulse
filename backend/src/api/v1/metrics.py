from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.services import metrics_service

router = APIRouter()


@router.get("")
async def read_metrics() -> dict[str, Any]:
    return await metrics_service.metrics_snapshot()
