"""Administrative configuration."""

from __future__ import annotations

from typing import Any


async def get_settings_summary() -> dict[str, Any]:
    return {"environment": "development"}
