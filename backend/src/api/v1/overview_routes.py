from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.overview_schemas import OverviewSummary
from src.services.overview_service import get_overview_summary

router = APIRouter(tags=["overview"])


@router.get("", response_model=OverviewSummary)
async def get_overview(db: Session = Depends(get_db)) -> OverviewSummary:
    """Aggregated figures for the operations-overview landing dashboard."""
    return await get_overview_summary(db)
