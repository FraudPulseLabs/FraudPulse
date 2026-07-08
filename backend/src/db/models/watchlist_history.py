"""
`watchlist_history` is defined canonically in `watchlist_model.py`, alongside the
`Watchlist` relationship, and matches the live Supabase schema
(watchlist_entity_type / watchlist_entity_id / action / watchlist_reason /
risk_severity / is_blacklist / created_by / expires_at).

This module previously declared a SECOND, divergent WatchlistHistory mapping
(entity_type / entity_id / reason / actor) that did not exist in the database.
It now re-exports the canonical class so existing imports keep working without a
conflicting table definition.
"""
from __future__ import annotations

from src.db.models.watchlist_model import WatchlistHistory

__all__ = ["WatchlistHistory"]
