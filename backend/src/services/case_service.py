#backend\src\services\case_service.py
"""Investigation case workflows, notes, and event timeline."""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.case_model import Case, CaseEvent, CaseNote
from src.schemas.case_schemas import (
    CaseEventType,
    CaseNoteCreate,
    CaseRiskLevel,
    CaseStatus,
    CaseUpdate,
)
from src.services.event_emitter import event_emitter


# =============================================================================
# Helpers
# =============================================================================

def _make_title(transaction_id: uuid.UUID) -> str:
    short = str(transaction_id).split("-")[0].upper()
    return f"Fraud Investigation – TXN {short}"


def _write_event(
    db: Session,
    case_id: uuid.UUID,
    event_type: CaseEventType,
    description: str,
    actor: str = "system",
) -> CaseEvent:
    event = CaseEvent(
        case_id=case_id,
        event_type=event_type.value,
        description=description,
        actor=actor,
    )
    db.add(event)
    return event


# =============================================================================
# Cases
# =============================================================================

def create_case(
    db: Session,
    transaction_id: uuid.UUID,
    title: str | None = None,
    risk_level: CaseRiskLevel = CaseRiskLevel.MEDIUM,
) -> Case:
    case = Case(
        transaction_id=transaction_id,
        title=title or _make_title(transaction_id),
        status=CaseStatus.OPEN.value,
        risk_level=risk_level.value,
    )
    db.add(case)
    db.flush()

    _write_event(
        db=db,
        case_id=case.id,
        event_type=CaseEventType.ALERT_ADDED,
        description="Case opened automatically from fraud alert",
        actor="system",
    )

    return case


async def list_cases(
    db: Session,
    status: CaseStatus | None = None,
    risk_level: CaseRiskLevel | None = None,
    assigned_to: uuid.UUID | None = None,
) -> list[Case]:
    query = select(Case)

    if status:
        query = query.where(Case.status == status.value)
    if risk_level:
        query = query.where(Case.risk_level == risk_level.value)
    if assigned_to:
        query = query.where(Case.assigned_to == assigned_to)

    return db.execute(query.order_by(Case.created_at.desc())).scalars().all()


async def get_case(db: Session, case_id: uuid.UUID) -> Case:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


async def update_case(
    db: Session,
    case_id: uuid.UUID,
    payload: CaseUpdate,
    actor: str = "analyst",
) -> Case:
    case = await get_case(db, case_id)

    if payload.status is not None:
        old_status = case.status
        case.status = payload.status.value
        desc = f"Status changed from {old_status} to {payload.status.value}"
        if payload.resolution_code:
            desc += f" — {payload.resolution_code.value}"
        _write_event(db, case.id, CaseEventType.STATUS_CHANGED, desc, actor)

    if payload.risk_level is not None:
        case.risk_level = payload.risk_level.value

    if payload.resolution_code is not None:
        case.resolution_code = payload.resolution_code.value

    if payload.assigned_to is not None:
        case.assigned_to = payload.assigned_to
        _write_event(
            db, case.id,
            CaseEventType.ASSIGNMENT_CHANGED,
            f"Case assigned to {payload.assigned_to}",
            actor,
        )

    db.flush()
    return case


# =============================================================================
# Case notes
# =============================================================================

def create_case_note(
    db: Session,
    case_id: uuid.UUID,
    payload: CaseNoteCreate,
) -> CaseNote:
    if db.get(Case, case_id) is None:
        raise HTTPException(status_code=404, detail="Case not found")

    note = CaseNote(
        case_id=case_id,
        author_id=payload.author_id,
        body=payload.body,
    )
    db.add(note)
    db.flush()

    _write_event(
        db=db,
        case_id=case_id,
        event_type=CaseEventType.NOTE_ADDED,
        description="Note added",
        actor=payload.author_id,
    )

    return note


def list_case_notes(db: Session, case_id: uuid.UUID) -> list[CaseNote]:
    return (
        db.execute(
            select(CaseNote)
            .where(CaseNote.case_id == case_id)
            .order_by(CaseNote.created_at)
        )
        .scalars()
        .all()
    )


# =============================================================================
# Case events (timeline)
# =============================================================================

def list_case_events(db: Session, case_id: uuid.UUID) -> list[CaseEvent]:
    return (
        db.execute(
            select(CaseEvent)
            .where(CaseEvent.case_id == case_id)
            .order_by(CaseEvent.created_at.desc())
        )
        .scalars()
        .all()
    )


# =============================================================================
# Event handler
# =============================================================================

def handle_case_creation(db: Session, transaction_id: uuid.UUID) -> None:
    create_case(db=db, transaction_id=transaction_id)


event_emitter.subscribe("fraud_review_required", handle_case_creation)