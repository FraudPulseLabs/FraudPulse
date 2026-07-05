"""Aggregation for the operations-overview dashboard.

One DB round-trip produces the four headline counters plus the two short lists
(priority alerts, active investigations) the overview renders above the fold.
Heavy per-entity detail stays on the dedicated endpoints.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.db.models.alert_model import Alert
from src.db.models.case_model import Case
from src.db.models.transaction import Transaction
from src.db.models.watchlist_model import Watchlist
from src.schemas.alert_schemas import AlertRead, AlertSeverity
from src.schemas.case_schemas import CaseRead, CaseStatus
from src.schemas.overview_schemas import OverviewCounts, OverviewSummary

# Cases the analyst still needs to act on.
_ACTIVE_CASE_STATUSES = (CaseStatus.OPEN.value, CaseStatus.INVESTIGATING.value)

# How many records to surface in each above-the-fold list.
_LIST_LIMIT = 5


async def get_overview_summary(db: Session) -> OverviewSummary:
    now = datetime.now(timezone.utc)

    recent_transactions = db.execute(
        select(func.count()).select_from(Transaction)
    ).scalar_one()

    open_alerts = db.execute(
        select(func.count()).select_from(Alert)
    ).scalar_one()

    active_cases_count = db.execute(
        select(func.count())
        .select_from(Case)
        .where(Case.status.in_(_ACTIVE_CASE_STATUSES))
    ).scalar_one()

    watchlist_entries = db.execute(
        select(func.count())
        .select_from(Watchlist)
        .where(or_(Watchlist.expires_at.is_(None), Watchlist.expires_at > now))
    ).scalar_one()

    priority_alerts = (
        db.execute(
            select(Alert)
            .where(Alert.severity == AlertSeverity.HIGH.value)
            .order_by(Alert.created_at.desc())
            .limit(_LIST_LIMIT)
        )
        .scalars()
        .all()
    )

    active_cases = (
        db.execute(
            select(Case)
            .where(Case.status.in_(_ACTIVE_CASE_STATUSES))
            .order_by(Case.updated_at.desc())
            .limit(_LIST_LIMIT)
        )
        .scalars()
        .all()
    )

    return OverviewSummary(
        counts=OverviewCounts(
            recent_transactions=recent_transactions,
            open_alerts=open_alerts,
            active_cases=active_cases_count,
            watchlist_entries=watchlist_entries,
        ),
        priority_alerts=[AlertRead.model_validate(a) for a in priority_alerts],
        active_cases=[CaseRead.model_validate(c) for c in active_cases],
    )
