# src/api/v1/watchlist_routes.py

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.watchlist_schemas import (
    ApiResponse,
    EntityType,
    RiskSeverity,
    WatchlistCreate,
    WatchlistUpdate,
)
from src.services.watchlist_service import (
    add_watchlist_entry,
    get_watchlist_entries,
    remove_watchlist_entry,
    update_watchlist_entry,
)

router = APIRouter(tags=["Watchlist"])


@router.get("", response_model=ApiResponse)
async def list_watchlist(
    include_expired: bool = False,
    entity_type: EntityType | None = None,
    entity_id: str | None = None,
    risk_severity: RiskSeverity | None = None,
    is_blacklist: bool | None = None,
    watchlist_reason: str | None = None,
    db: Session = Depends(get_db),
) -> ApiResponse:
    entries = await get_watchlist_entries(
        db=db,
        include_expired=include_expired,
        entity_type=entity_type,
        entity_id=entity_id,
        risk_severity=risk_severity,
        is_blacklist=is_blacklist,
        watchlist_reason=watchlist_reason,
    )
    return ApiResponse(
        success=True,
        message="Watchlist entries retrieved successfully",
        data=entries,
    )


@router.post("", response_model=ApiResponse, status_code=201)
async def create_watchlist_entry(
    payload: WatchlistCreate,
    db: Session = Depends(get_db),
) -> ApiResponse:
    entry = await add_watchlist_entry(db=db, payload=payload)
    return ApiResponse(
        success=True,
        message="Watchlist entry created successfully",
        data=entry,
    )


@router.patch("/{entity_type}/{entity_id}", response_model=ApiResponse)
async def edit_watchlist_entry(
    entity_type: EntityType,
    entity_id: str,
    payload: WatchlistUpdate,
    db: Session = Depends(get_db),
) -> ApiResponse:
    updated = await update_watchlist_entry(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
    )
    return ApiResponse(
        success=True,
        message="Watchlist entry updated successfully",
        data=updated,
    )


@router.delete("/{entity_type}/{entity_id}", response_model=ApiResponse)
async def delete_watchlist_entry(
    entity_type: EntityType,
    entity_id: str,
    db: Session = Depends(get_db),
) -> ApiResponse:
    await remove_watchlist_entry(db=db, entity_type=entity_type, entity_id=entity_id)
    return ApiResponse(
        success=True,
        message="Watchlist entry removed successfully",
        data=None,
    )