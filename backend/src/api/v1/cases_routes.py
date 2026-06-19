# src/api/v1/cases.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.case_schemas import (
    CaseEventRead,
    CaseNoteCreate,
    CaseNoteRead,
    CaseRead,
    CaseRiskLevel,
    CaseStatus,
    CaseUpdate,
)
from src.services.case_service import (
    create_case_note,
    get_case,
    list_case_events,
    list_case_notes,
    list_cases,
    update_case,
)

router = APIRouter(tags=["cases"])


# =============================================================================
# Cases
# =============================================================================

@router.get("", response_model=list[CaseRead])
async def list_cases_route(
    status: CaseStatus | None = None,
    risk_level: CaseRiskLevel | None = None,
    assigned_to: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[CaseRead]:
    return await list_cases(db=db, status=status, risk_level=risk_level, assigned_to=assigned_to)


@router.get("/{case_id}", response_model=CaseRead)
async def get_case_by_id(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> CaseRead:
    return await get_case(db=db, case_id=case_id)


@router.patch("/{case_id}", response_model=CaseRead)
async def patch_case(
    case_id: uuid.UUID,
    payload: CaseUpdate,
    db: Session = Depends(get_db),
) -> CaseRead:
    case = await update_case(db=db, case_id=case_id, payload=payload)
    db.commit()
    return case


# =============================================================================
# Case notes
# =============================================================================

@router.get("/{case_id}/notes", response_model=list[CaseNoteRead])
async def list_notes(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[CaseNoteRead]:
    return list_case_notes(db=db, case_id=case_id)


@router.post("/{case_id}/notes", response_model=CaseNoteRead, status_code=201)
async def add_note(
    case_id: uuid.UUID,
    payload: CaseNoteCreate,
    db: Session = Depends(get_db),
) -> CaseNoteRead:
    note = create_case_note(db=db, case_id=case_id, payload=payload)
    db.commit()
    return note


# =============================================================================
# Case events (timeline)
# =============================================================================

@router.get("/{case_id}/events", response_model=list[CaseEventRead])
async def list_events(
    case_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[CaseEventRead]:
    return list_case_events(db=db, case_id=case_id)