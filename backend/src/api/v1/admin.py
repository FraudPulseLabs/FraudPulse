from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.services import admin_service

router = APIRouter()


@router.get("/settings")
async def settings_summary() -> dict[str, Any]:
    return await admin_service.get_settings_summary()
