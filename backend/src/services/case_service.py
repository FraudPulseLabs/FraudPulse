#backend\src\services\case_service.py
"""Investigation case workflows."""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.db.models.case_model import Case
from src.schemas.case_schemas import CaseRiskLevel, CaseStatus, CaseUpdate
from src.services.event_emitter import event_emitter


def _make_title(transaction_id: uuid.UUID) -> str:
    short = str(transaction_id).split("-")[0].upper()
    return f"Fraud Investigation – TXN {short}"


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

    return (
        db.execute(query.order_by(Case.created_at.desc()))
        .scalars()
        .all()
    )


async def get_case(
    db: Session,
    case_id: uuid.UUID,
) -> Case:
    case = db.get(Case, case_id)

    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")

    return case


async def update_case(
    db: Session,
    case_id: uuid.UUID,
    payload: CaseUpdate,
) -> Case:
    case = await get_case(db, case_id)

    if payload.status is not None:
        case.status = payload.status.value

    if payload.risk_level is not None:
        case.risk_level = payload.risk_level.value

    if payload.resolution_code is not None:
        case.resolution_code = payload.resolution_code.value

    if payload.assigned_to is not None:
        case.assigned_to = payload.assigned_to

    db.flush()

    return case


def handle_case_creation(
    db: Session,
    transaction_id: uuid.UUID,
) -> None:
    create_case(db=db, transaction_id=transaction_id)


event_emitter.subscribe("fraud_review_required", handle_case_creation)