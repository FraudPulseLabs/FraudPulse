"""Investigation case workflows."""

from __future__ import annotations

from typing import Any


async def list_cases() -> list[dict[str, Any]]:
    return []


async def get_case(case_id: int) -> dict[str, Any] | None:
    return {"id": case_id, "status": None}
