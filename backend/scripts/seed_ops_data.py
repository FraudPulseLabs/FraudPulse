"""
Drop and reseed alerts, cases, and watchlist with Kenya-focused demo data.

Uses existing KES / Kenya-corridor transactions already in the database.

Run from backend/:
    python -m scripts.seed_ops_data
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.core.config import DATABASE_URL
from src.db.models.alert_model import Alert
from src.db.models.case_model import Case, CaseEvent, CaseNote
from src.db.models.transaction import Transaction
from src.db.models.watchlist_model import Watchlist, WatchlistHistory
from src.db.session import SessionLocal
from src.schemas.alert_schemas import AlertReason, AlertSeverity
from src.schemas.case_schemas import CaseEventType, CaseRiskLevel, CaseStatus

ANALYST = "analyst@fraudpulse.demo"
LEAD = "lead@fraudpulse.demo"
NOW = datetime.now(timezone.utc)

KENYA_COUNTRIES = ("KEN", "KE")


def _ago(**kwargs: float | int) -> datetime:
    return NOW - timedelta(**kwargs)  # type: ignore[arg-type]


def _kenya_transactions(db: Session) -> list[Transaction]:
    """Domestic Kenya payments in KES."""
    rows = db.execute(
        select(Transaction)
        .where(
            Transaction.transaction_currency == "KES",
            Transaction.transaction_country.in_(KENYA_COUNTRIES),
        )
        .order_by(Transaction.created_at.desc())
    ).scalars().all()
    return list(rows)


def clear_ops_tables(db: Session) -> None:
    db.execute(delete(WatchlistHistory))
    db.execute(delete(Watchlist))
    db.execute(delete(Alert))
    db.execute(delete(CaseEvent))
    db.execute(delete(CaseNote))
    db.execute(delete(Case))
    db.flush()
    print("Cleared alerts, cases, watchlist (and related notes/events/history).")


def _require_kenya_tx(db: Session, txn_id: uuid.UUID) -> Transaction:
    txn = db.get(Transaction, txn_id)
    if txn is None:
        raise RuntimeError(f"Transaction {txn_id} not found — seed requires existing rows.")
    if txn.transaction_currency != "KES" or txn.transaction_country not in KENYA_COUNTRIES:
        raise RuntimeError(f"Transaction {txn_id} is not a Kenya KES payment.")
    return txn


def _txn_by_merchant(txns: list[Transaction], merchant_id: str) -> list[Transaction]:
    return [t for t in txns if t.merchant_id == merchant_id]


def seed_watchlist(db: Session, txns: list[Transaction]) -> None:
    atm_txn = _txn_by_merchant(txns, "merch_test_001")[0]
    pos_txn = next(t for t in txns if t.merchant_id == "m_c9ab694da52f")
    retail_txn = next(t for t in txns if t.merchant_id == "m_47d74a000558")

    entries: list[dict] = [
        {
            "watchlist_entity_type": "MERCHANT",
            "watchlist_entity_id": "merch_test_001",
            "watchlist_reason": "Repeated high-value ATM withdrawals at Nairobi CBD terminal",
            "risk_severity": "HIGH",
            "is_blacklist": True,
            "created_by": ANALYST,
            "expires_at": None,
            "created_at": _ago(days=8),
        },
        {
            "watchlist_entity_type": "MERCHANT",
            "watchlist_entity_id": "m_c9ab694da52f",
            "watchlist_reason": "Elevated chargeback rate at coastal supermarket POS",
            "risk_severity": "MEDIUM",
            "is_blacklist": False,
            "created_by": ANALYST,
            "expires_at": NOW + timedelta(days=21),
            "created_at": _ago(days=6),
        },
        {
            "watchlist_entity_type": "MERCHANT",
            "watchlist_entity_id": "m_47d74a000558",
            "watchlist_reason": "Low-value card testing at Nairobi retail outlets",
            "risk_severity": "LOW",
            "is_blacklist": False,
            "created_by": ANALYST,
            "expires_at": NOW + timedelta(days=30),
            "created_at": _ago(days=10),
        },
        {
            "watchlist_entity_type": "MERCHANT",
            "watchlist_entity_id": "m_7471a28c8921",
            "watchlist_reason": "Mobile-money airtime purchases under review",
            "risk_severity": "MEDIUM",
            "is_blacklist": False,
            "created_by": LEAD,
            "expires_at": NOW + timedelta(days=14),
            "created_at": _ago(days=4),
        },
        {
            "watchlist_entity_type": "MERCHANT",
            "watchlist_entity_id": "m_942392030c9f",
            "watchlist_reason": "Unusual ATM withdrawal velocity on Kenyan debit cards",
            "risk_severity": "MEDIUM",
            "is_blacklist": False,
            "created_by": ANALYST,
            "expires_at": NOW + timedelta(days=21),
            "created_at": _ago(days=5),
        },
        {
            "watchlist_entity_type": "USER",
            "watchlist_entity_id": "card_test_002",
            "watchlist_reason": "Multiple 200,000 KES ATM withdrawals within 24 hours",
            "risk_severity": "HIGH",
            "is_blacklist": False,
            "created_by": ANALYST,
            "expires_at": NOW + timedelta(days=7),
            "created_at": _ago(days=3),
        },
        {
            "watchlist_entity_type": "USER",
            "watchlist_entity_id": "card_test_001",
            "watchlist_reason": "Same card used for ATM cash-out and e-commerce within minutes",
            "risk_severity": "MEDIUM",
            "is_blacklist": False,
            "created_by": ANALYST,
            "expires_at": NOW + timedelta(days=14),
            "created_at": _ago(days=2),
        },
        {
            "watchlist_entity_type": "USER",
            "watchlist_entity_id": "c_b6bb7a5723da",
            "watchlist_reason": "Biometric POS spend spike vs cardholder baseline",
            "risk_severity": "MEDIUM",
            "is_blacklist": False,
            "created_by": LEAD,
            "expires_at": NOW + timedelta(days=14),
            "created_at": _ago(days=3),
        },
        {
            "watchlist_entity_type": "TRANSACTION",
            "watchlist_entity_id": str(atm_txn.id),
            "watchlist_reason": "Held for review — large Nairobi ATM withdrawal flagged by model",
            "risk_severity": "MEDIUM",
            "is_blacklist": False,
            "created_by": ANALYST,
            "expires_at": NOW + timedelta(days=5),
            "created_at": _ago(hours=6),
        },
        {
            "watchlist_entity_type": "TRANSACTION",
            "watchlist_entity_id": str(pos_txn.id),
            "watchlist_reason": "Mombasa supermarket POS pending analyst review",
            "risk_severity": "LOW",
            "is_blacklist": False,
            "created_by": LEAD,
            "expires_at": NOW + timedelta(days=7),
            "created_at": _ago(days=1),
        },
        {
            "watchlist_entity_type": "TRANSACTION",
            "watchlist_entity_id": str(retail_txn.id),
            "watchlist_reason": "Nairobi retail POS — authentication mismatch",
            "risk_severity": "LOW",
            "is_blacklist": False,
            "created_by": ANALYST,
            "expires_at": NOW + timedelta(days=10),
            "created_at": _ago(days=2),
        },
    ]

    for row in entries:
        entry = Watchlist(
            watchlist_entity_type=row["watchlist_entity_type"],
            watchlist_entity_id=row["watchlist_entity_id"],
            watchlist_reason=row["watchlist_reason"],
            risk_severity=row["risk_severity"],
            is_blacklist=row["is_blacklist"],
            created_by=row["created_by"],
            expires_at=row["expires_at"],
            created_at=row["created_at"],
        )
        db.add(entry)
        db.flush()
        db.add(
            WatchlistHistory(
                watchlist_id=entry.id,
                watchlist_entity_type=entry.watchlist_entity_type,
                watchlist_entity_id=entry.watchlist_entity_id,
                action="ADDED",
                watchlist_reason=entry.watchlist_reason,
                risk_severity=entry.risk_severity,
                is_blacklist=entry.is_blacklist,
                created_by=entry.created_by,
                expires_at=entry.expires_at,
                created_at=entry.created_at,
            )
        )

    print(f"Inserted {len(entries)} Kenya watchlist entries.")


def seed_alerts(db: Session, txns: list[Transaction]) -> None:
    merch_atm = [t for t in _txn_by_merchant(txns, "merch_test_001") if t.decision == "APPROVE_WITH_REVIEW"]
    pos_review = [t for t in txns if t.merchant_id == "m_942392030c9f" and t.decision == "APPROVE_WITH_REVIEW"]
    mobile = _txn_by_merchant(txns, "m_7471a28c8921")

    specs: list[tuple[uuid.UUID, AlertReason, AlertSeverity, datetime]] = [
        (merch_atm[0].id, AlertReason.FRAUD_REVIEW_REQUIRED, AlertSeverity.MEDIUM, _ago(hours=5)),
        (merch_atm[1].id, AlertReason.FRAUD_REVIEW_REQUIRED, AlertSeverity.MEDIUM, _ago(days=1)),
        (merch_atm[2].id, AlertReason.MERCHANT_BLACKLISTED, AlertSeverity.HIGH, _ago(days=3)),
        (merch_atm[3].id, AlertReason.MERCHANT_BLACKLISTED, AlertSeverity.HIGH, _ago(days=6)),
        (pos_review[0].id, AlertReason.FRAUD_REVIEW_REQUIRED, AlertSeverity.MEDIUM, _ago(days=2)),
        (mobile[0].id, AlertReason.FRAUD_REVIEW_REQUIRED, AlertSeverity.LOW, _ago(days=4)),
        (next(t for t in txns if t.merchant_id == "m_c9ab694da52f").id, AlertReason.FRAUD_REVIEW_REQUIRED, AlertSeverity.LOW, _ago(days=5)),
        (next(t for t in txns if t.merchant_id == "m_47d74a000558").id, AlertReason.FRAUD_REVIEW_REQUIRED, AlertSeverity.LOW, _ago(days=1, hours=12)),
    ]

    for txn_id, reason, severity, created_at in specs:
        _require_kenya_tx(db, txn_id)
        db.add(
            Alert(
                transaction_id=txn_id,
                reason=reason.value,
                severity=severity.value,
                created_at=created_at,
            )
        )

    db.flush()
    print(f"Inserted {len(specs)} Kenya alerts.")


def _add_case(
    db: Session,
    *,
    transaction_id: uuid.UUID,
    title: str,
    status: CaseStatus,
    risk_level: CaseRiskLevel,
    resolution_code: str | None,
    created_at: datetime,
    updated_at: datetime,
) -> Case:
    _require_kenya_tx(db, transaction_id)
    case = Case(
        transaction_id=transaction_id,
        title=title,
        status=status.value,
        risk_level=risk_level.value,
        resolution_code=resolution_code,
        created_at=created_at,
        updated_at=updated_at,
    )
    db.add(case)
    db.flush()
    return case


def _add_event(
    db: Session,
    *,
    case_id: uuid.UUID,
    event_type: CaseEventType,
    description: str,
    actor: str,
    created_at: datetime,
) -> None:
    db.add(
        CaseEvent(
            case_id=case_id,
            event_type=event_type.value,
            description=description,
            actor=actor,
            created_at=created_at,
        )
    )


def _add_note(
    db: Session,
    *,
    case_id: uuid.UUID,
    author_id: str,
    body: str,
    created_at: datetime,
) -> None:
    db.add(
        CaseNote(
            case_id=case_id,
            author_id=author_id,
            body=body,
            created_at=created_at,
        )
    )


def seed_cases(db: Session, txns: list[Transaction]) -> None:
    merch_atm = [t for t in _txn_by_merchant(txns, "merch_test_001") if t.decision == "APPROVE_WITH_REVIEW"]
    pos_merchant = next(t for t in txns if t.merchant_id == "m_c9ab694da52f")
    atm_network = next(t for t in txns if t.merchant_id == "m_942392030c9f" and t.decision == "APPROVE_WITH_REVIEW")
    mobile = next(t for t in txns if t.merchant_id == "m_7471a28c8921")

    cases_spec = [
        {
            "transaction_id": merch_atm[0].id,
            "title": "Nairobi ATM cash-out surge — card_test_002",
            "status": CaseStatus.OPEN,
            "risk_level": CaseRiskLevel.HIGH,
            "resolution_code": None,
            "created_at": _ago(hours=5),
            "updated_at": _ago(hours=1),
            "events": [
                (CaseEventType.ALERT_ADDED, "Case opened from FRAUD_REVIEW_REQUIRED alert", ANALYST, _ago(hours=5)),
                (CaseEventType.STATUS_CHANGED, "Status set to OPEN — awaiting initial review", "system", _ago(hours=5)),
            ],
            "notes": [
                (ANALYST, "200,000 KES ATM withdrawal in Nairobi with no OTP. Card flagged for velocity.", _ago(hours=4)),
            ],
        },
        {
            "transaction_id": atm_network.id,
            "title": "Kenyan ATM network — elevated POS review",
            "status": CaseStatus.INVESTIGATING,
            "risk_level": CaseRiskLevel.MEDIUM,
            "resolution_code": None,
            "created_at": _ago(days=2),
            "updated_at": _ago(days=1),
            "events": [
                (CaseEventType.ALERT_ADDED, "Review alert for elevated fraud score on Kenyan ATM corridor", ANALYST, _ago(days=2)),
                (CaseEventType.ASSIGNMENT_CHANGED, f"Case assigned to {ANALYST}", LEAD, _ago(days=1, hours=6)),
            ],
            "notes": [
                (ANALYST, "460 KES POS with weak auth at Kenyan ATM merchant. Pattern warrants follow-up.", _ago(days=1)),
            ],
        },
        {
            "transaction_id": merch_atm[2].id,
            "title": "Blacklisted merchant — Nairobi ATM terminal cluster",
            "status": CaseStatus.OPEN,
            "risk_level": CaseRiskLevel.HIGH,
            "resolution_code": None,
            "created_at": _ago(days=3),
            "updated_at": _ago(days=2),
            "events": [
                (CaseEventType.ALERT_ADDED, "MERCHANT_BLACKLISTED alert auto-generated", "system", _ago(days=3)),
            ],
            "notes": [
                (LEAD, "Merchant blacklisted after structured KES ATM withdrawals. SAR recommended.", _ago(days=2)),
            ],
        },
        {
            "transaction_id": pos_merchant.id,
            "title": "Mombasa supermarket POS — biometric verification",
            "status": CaseStatus.CLOSED,
            "risk_level": CaseRiskLevel.LOW,
            "resolution_code": "FALSE_POSITIVE",
            "created_at": _ago(days=14),
            "updated_at": _ago(days=10),
            "events": [
                (CaseEventType.ALERT_ADDED, "Case opened from routine Kenya POS review", ANALYST, _ago(days=14)),
                (CaseEventType.STATUS_CHANGED, "Status changed to CLOSED — FALSE_POSITIVE", LEAD, _ago(days=10)),
            ],
            "notes": [
                (ANALYST, "Cardholder confirmed grocery purchase in Mombasa. Legitimate KES 4.89 charge.", _ago(days=11)),
            ],
        },
        {
            "transaction_id": merch_atm[3].id,
            "title": "Structured ATM withdrawals — card_test_001",
            "status": CaseStatus.CLOSED,
            "risk_level": CaseRiskLevel.HIGH,
            "resolution_code": "CONFIRMED_FRAUD",
            "created_at": _ago(days=20),
            "updated_at": _ago(days=15),
            "events": [
                (CaseEventType.ALERT_ADDED, "Blacklisted merchant alert on repeated Nairobi ATM activity", "system", _ago(days=20)),
                (CaseEventType.STATUS_CHANGED, "Status changed to INVESTIGATING", LEAD, _ago(days=18)),
                (CaseEventType.STATUS_CHANGED, "Status changed to CLOSED — CONFIRMED_FRAUD", LEAD, _ago(days=15)),
            ],
            "notes": [
                (LEAD, "Pattern matches mule cash-out: five 200K KES ATM txs in 48h across Nairobi.", _ago(days=17)),
                (ANALYST, "Card blocked. Terminal merchant added to blacklist.", _ago(days=15)),
            ],
        },
        {
            "transaction_id": mobile.id,
            "title": "Mobile-money airtime — low-value e-commerce review",
            "status": CaseStatus.OPEN,
            "risk_level": CaseRiskLevel.LOW,
            "resolution_code": None,
            "created_at": _ago(days=1),
            "updated_at": _ago(hours=12),
            "events": [
                (CaseEventType.ALERT_ADDED, "Review alert for Kenyan mobile-money purchase", ANALYST, _ago(days=1)),
            ],
            "notes": [],
        },
    ]

    for spec in cases_spec:
        case = _add_case(
            db,
            transaction_id=spec["transaction_id"],
            title=spec["title"],
            status=spec["status"],
            risk_level=spec["risk_level"],
            resolution_code=spec["resolution_code"],
            created_at=spec["created_at"],
            updated_at=spec["updated_at"],
        )
        for event_type, description, actor, ts in spec["events"]:
            _add_event(db, case_id=case.id, event_type=event_type, description=description, actor=actor, created_at=ts)
        for author, body, ts in spec["notes"]:
            _add_note(db, case_id=case.id, author_id=author, body=body, created_at=ts)

    print(f"Inserted {len(cases_spec)} Kenya cases with notes and events.")


def main() -> None:
    if not DATABASE_URL:
        raise SystemExit("DATABASE_URL not set; cannot seed.")

    db = SessionLocal()
    try:
        kenya_txns = _kenya_transactions(db)
        if len(kenya_txns) < 6:
            raise SystemExit(
                "Not enough Kenya KES transactions in the database — ingest domestic payments first."
            )

        clear_ops_tables(db)
        seed_watchlist(db, kenya_txns)
        seed_alerts(db, kenya_txns)
        seed_cases(db, kenya_txns)
        db.commit()
        print("Kenya ops data seed complete.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
