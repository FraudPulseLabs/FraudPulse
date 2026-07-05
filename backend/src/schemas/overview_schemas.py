"""Response schema for the aggregated operations-overview endpoint.

The overview dashboard needs a handful of counters plus two short record lists.
Rather than have the frontend fan out to /transactions, /alerts, /cases and
/watchlist on load, this single payload lets the backend do the aggregation in
one round-trip. Full records are still fetched from the individual endpoints
when the analyst drills into a card.
"""
from __future__ import annotations

from pydantic import BaseModel

from src.schemas.alert_schemas import AlertRead
from src.schemas.case_schemas import CaseRead


class OverviewCounts(BaseModel):
    recent_transactions: int
    open_alerts: int
    active_cases: int
    watchlist_entries: int


class OverviewSummary(BaseModel):
    counts: OverviewCounts
    priority_alerts: list[AlertRead]
    active_cases: list[CaseRead]
