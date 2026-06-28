"""Unit tests for the exact-match merchant blacklist helper."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.services.watchlist_service import is_merchant_blacklisted


def _db_returning(entry):
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = entry
    return db


def test_no_entry_returns_false():
    assert is_merchant_blacklisted(_db_returning(None), "MRCH-1") is False


def test_active_blacklist_entry_returns_true():
    future = datetime.now(timezone.utc) + timedelta(days=7)
    entry = SimpleNamespace(expires_at=future)
    assert is_merchant_blacklisted(_db_returning(entry), "MRCH-1") is True


def test_blacklist_entry_with_no_expiry_returns_true():
    entry = SimpleNamespace(expires_at=None)
    assert is_merchant_blacklisted(_db_returning(entry), "MRCH-1") is True


def test_expired_blacklist_entry_returns_false():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    entry = SimpleNamespace(expires_at=past)
    assert is_merchant_blacklisted(_db_returning(entry), "MRCH-1") is False
