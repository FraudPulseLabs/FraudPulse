from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.services import case_service

router = APIRouter()


@router.get("")
async def list_cases() -> list[dict[str, Any]]:
    return await case_service.list_cases()


@router.get("/{case_id}")
async def get_case(case_id: int) -> dict[str, Any] | None:
    return await case_service.get_case(case_id)
