"""
GET /api/v1/demo/transactions

Returns the static set of held-out test-split transactions used by the
frontend "Model Demo" page. Each record includes the full POST
/api/v1/transactions payload plus the ground-truth `is_fraud` label.

is_fraud is for display / predicted-vs-actual comparison only. It is NEVER
consumed by the scoring pipeline — the frontend strips it before POSTing.

The artifact is produced by backend/scripts/seed_demo_transactions.py and
committed to the repo; this endpoint just reads and returns it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter()

_DEMO_PATH = (
    Path(__file__).resolve().parents[3]
    / "ml"
    / "data"
    / "demo"
    / "demo_transactions.json"
)


@router.get("/transactions")
async def list_demo_transactions() -> list[dict[str, Any]]:
    if not _DEMO_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail=(
                "Demo artifact missing. Run "
                "`python -m scripts.seed_demo_transactions` from the backend dir."
            ),
        )
    return json.loads(_DEMO_PATH.read_text())
