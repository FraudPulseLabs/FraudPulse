from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.services import decision_service

router = APIRouter()


@router.post("")
async def decide(body: dict[str, Any]) -> dict[str, Any]:
    return await decision_service.decide(body)
