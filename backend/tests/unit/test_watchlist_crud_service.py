"""Unit tests for watchlist_service CRUD beyond blacklist helper."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.db.models.watchlist_model import Watchlist
from src.schemas.watchlist_schemas import EntityType, RiskSeverity, WatchlistCreate, WatchlistUpdate
from src.services import watchlist_service


def _entry(
    *,
    entity_type: str = EntityType.MERCHANT.value,
    entity_id: str = "MRCH-1",
    is_blacklist: bool = False,
    expires_at: datetime | None = None,
) -> Watchlist:
    row = Watchlist(
        watchlist_entity_type=entity_type,
        watchlist_entity_id=entity_id,
        watchlist_reason="Test reason",
        risk_severity=RiskSeverity.MEDIUM.value,
        is_blacklist=is_blacklist,
        created_by="analyst@test.com",
        expires_at=expires_at,
    )
    row.id = uuid.uuid4()
    row.created_at = datetime.now(timezone.utc)
    return row


class TestGetWatchlistEntries:
    def test_returns_validated_reads(self):
        row = _entry()
        db = MagicMock()
        db.execute.return_value.scalars.return_value.all.return_value = [row]

        result = asyncio.run(watchlist_service.get_watchlist_entries(db=db))

        assert len(result) == 1
        assert result[0].watchlist_entity_id == "MRCH-1"


class TestAddWatchlistEntry:
    def test_creates_new_entry(self):
        db = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = None

        def _assign_ids(obj):
            if isinstance(obj, Watchlist):
                obj.id = uuid.uuid4()
                obj.created_at = datetime.now(timezone.utc)

        db.add.side_effect = _assign_ids

        payload = WatchlistCreate(
            watchlist_entity_type=EntityType.MERCHANT,
            watchlist_entity_id="MRCH-NEW",
            watchlist_reason="Velocity review",
            risk_severity=RiskSeverity.HIGH,
            is_blacklist=False,
            created_by="analyst@test.com",
            expires_at=None,
        )

        result = asyncio.run(watchlist_service.add_watchlist_entry(db=db, payload=payload))

        assert result.watchlist_entity_id == "MRCH-NEW"
        db.add.assert_called()
        db.flush.assert_called()

    def test_raises_409_when_active_entry_exists(self):
        existing = _entry(expires_at=datetime.now(timezone.utc) + timedelta(days=7))
        db = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = existing

        payload = WatchlistCreate(
            watchlist_entity_type=EntityType.MERCHANT,
            watchlist_entity_id="MRCH-1",
            watchlist_reason="Duplicate",
            risk_severity=RiskSeverity.LOW,
            is_blacklist=False,
            created_by="analyst@test.com",
            expires_at=None,
        )

        with pytest.raises(HTTPException) as exc:
            asyncio.run(watchlist_service.add_watchlist_entry(db=db, payload=payload))

        assert exc.value.status_code == 409


class TestRemoveWatchlistEntry:
    def test_expires_existing_entry(self):
        row = _entry()
        db = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = row

        asyncio.run(
            watchlist_service.remove_watchlist_entry(
                db=db,
                entity_type=EntityType.MERCHANT,
                entity_id="MRCH-1",
            )
        )

        assert row.expires_at is not None
        db.commit.assert_called()

    def test_raises_404_when_missing(self):
        db = MagicMock()
        db.execute.return_value.scalar_one_or_none.return_value = None

        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                watchlist_service.remove_watchlist_entry(
                    db=db,
                    entity_type=EntityType.MERCHANT,
                    entity_id="MISSING",
                )
            )

        assert exc.value.status_code == 404
