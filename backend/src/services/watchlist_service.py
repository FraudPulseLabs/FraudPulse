# src/services/watchlist_service.py

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.db.models.watchlist_model import Watchlist, WatchlistHistory
from src.schemas.watchlist_schemas import (
    EntityType,
    HistoryAction,
    RiskSeverity,
    WatchlistCreate,
    WatchlistRead,
    WatchlistUpdate,
)


def _is_active(entry: Watchlist) -> bool:
    """Return True if the watchlist entry has not expired."""
    if entry.expires_at is None:
        return True
    return entry.expires_at > datetime.now(timezone.utc)


def _record_history(db: Session, entry: Watchlist, action: HistoryAction) -> None:
    """Append a row to watchlist_history reflecting the current state of entry."""
    db.add(
        WatchlistHistory(
            watchlist_id=entry.id,
            watchlist_entity_type=entry.watchlist_entity_type,
            watchlist_entity_id=entry.watchlist_entity_id,
            action=action,
            watchlist_reason=entry.watchlist_reason,
            risk_severity=entry.risk_severity,
            is_blacklist=entry.is_blacklist,
            created_by=entry.created_by,
            expires_at=entry.expires_at,
        )
    )


async def get_watchlist_entries(
    db: Session,
    include_expired: bool = False,
    entity_type: EntityType | None = None,
    entity_id: str | None = None,
    risk_severity: RiskSeverity | None = None,
    is_blacklist: bool | None = None,
    watchlist_reason: str | None = None,
) -> list[WatchlistRead]:
    query = select(Watchlist)

    if not include_expired:
        now = datetime.now(timezone.utc)
        query = query.where(
            or_(
                Watchlist.expires_at.is_(None),
                Watchlist.expires_at > now,
            )
        )

    if entity_type is not None:
        query = query.where(Watchlist.watchlist_entity_type == entity_type)

    if entity_id is not None:
        query = query.where(Watchlist.watchlist_entity_id.ilike(f"%{entity_id}%"))

    if risk_severity is not None:
        query = query.where(Watchlist.risk_severity == risk_severity)

    if is_blacklist is not None:
        query = query.where(Watchlist.is_blacklist == is_blacklist)

    if watchlist_reason is not None:
        query = query.where(Watchlist.watchlist_reason.ilike(f"%{watchlist_reason}%"))

    entries = db.execute(query).scalars().all()
    return [WatchlistRead.model_validate(e) for e in entries]


async def add_watchlist_entry(db: Session, payload: WatchlistCreate) -> WatchlistRead:
    existing = db.execute(
        select(Watchlist).where(
            Watchlist.watchlist_entity_type == payload.watchlist_entity_type,
            Watchlist.watchlist_entity_id == payload.watchlist_entity_id,
        )
    ).scalar_one_or_none()

    if existing:
        if _is_active(existing):
            raise HTTPException(
                status_code=409,
                detail="An active watchlist entry already exists for this entity.",
            )

        # Reactivate expired entry
        existing.watchlist_reason = payload.watchlist_reason
        existing.risk_severity = payload.risk_severity
        existing.is_blacklist = payload.is_blacklist
        existing.created_by = payload.created_by
        existing.expires_at = payload.expires_at
        _record_history(db, existing, HistoryAction.ADDED)
        db.commit()
        db.refresh(existing)
        return WatchlistRead.model_validate(existing)

    entry = Watchlist(
        watchlist_entity_type=payload.watchlist_entity_type,
        watchlist_entity_id=payload.watchlist_entity_id,
        watchlist_reason=payload.watchlist_reason,
        risk_severity=payload.risk_severity,
        is_blacklist=payload.is_blacklist,
        created_by=payload.created_by,
        expires_at=payload.expires_at,
    )
    db.add(entry)
    db.flush()  # populate entry.id before history insert
    _record_history(db, entry, HistoryAction.ADDED)
    db.commit()
    db.refresh(entry)
    return WatchlistRead.model_validate(entry)


async def update_watchlist_entry(
    db: Session,
    entity_type: EntityType,
    entity_id: str,
    payload: WatchlistUpdate,
) -> WatchlistRead:
    entry = db.execute(
        select(Watchlist).where(
            Watchlist.watchlist_entity_type == entity_type,
            Watchlist.watchlist_entity_id == entity_id,
        )
    ).scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found.")

    if not _is_active(entry):
        raise HTTPException(status_code=409, detail="Cannot update an expired watchlist entry.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)

    _record_history(db, entry, HistoryAction.UPDATED)
    db.commit()
    db.refresh(entry)
    return WatchlistRead.model_validate(entry)


async def remove_watchlist_entry(
    db: Session,
    entity_type: EntityType,
    entity_id: str,
) -> None:
    entry = db.execute(
        select(Watchlist).where(
            Watchlist.watchlist_entity_type == entity_type,
            Watchlist.watchlist_entity_id == entity_id,
        )
    ).scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found.")

    if not _is_active(entry):
        raise HTTPException(status_code=409, detail="Watchlist entry is already expired.")

    entry.expires_at = datetime.now(timezone.utc)
    _record_history(db, entry, HistoryAction.REMOVED)
    db.commit()