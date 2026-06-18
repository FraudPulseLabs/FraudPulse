# src/api/v1/profiles_routes.py
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.session import get_db

# Direct import — not via src.db.models.__init__ to avoid circular imports
from src.db.models.profile import Profile

router = APIRouter(tags=["profiles"])


class ProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    role: str
    is_active: bool
    created_at: datetime


@router.get("/analysts", response_model=list[ProfileRead])
async def list_analysts(
    db: Session = Depends(get_db),
) -> list[ProfileRead]:
    """Return all active FRAUD_ANALYST profiles for the case assignment picker."""
    rows = db.execute(
        select(Profile)
        .where(Profile.role == "FRAUD_ANALYST")
        .where(Profile.is_active == True)
        .order_by(Profile.full_name)
    ).scalars().all()

    return rows