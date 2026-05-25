from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.services import profile_service

router = APIRouter()


@router.get("")
async def list_profiles() -> list[dict[str, Any]]:
    return await profile_service.list_profiles()
