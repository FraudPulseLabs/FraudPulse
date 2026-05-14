"""Fraud scoring orchestration."""

from __future__ import annotations

from typing import Any


async def score_transaction(payload: dict[str, Any]) -> dict[str, Any]:
    return {"score": 0.0, "reasons": [], "model_version": "stub"}
