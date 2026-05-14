"""Operational metrics for dashboards."""

from __future__ import annotations

from typing import Any


async def metrics_snapshot() -> dict[str, Any]:
    return {"transactions_per_minute": 0, "alert_rate": 0.0}
