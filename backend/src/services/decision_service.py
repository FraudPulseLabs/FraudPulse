"""Transaction routing decisions (approve / review / decline)."""

from __future__ import annotations

from typing import Any


async def list_transactions() -> list[dict[str, Any]]:
    return []


async def decide(payload: dict[str, Any]) -> dict[str, Any]:
    return {"decision": "review", "transaction_id": payload.get("transaction_id")}
