from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.services import alerts_service

router = APIRouter()


@router.get("")
async def list_alerts() -> list[dict[str, Any]]:
    return await alerts_service.list_alerts()
