from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.services import watchlist_service

router = APIRouter()


@router.get("")
async def list_watchlist() -> list[dict[str, Any]]:
    return await watchlist_service.list_watchlist()
