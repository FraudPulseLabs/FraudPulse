# src/api/v1/cases.py
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.schemas.case_schemas import (
    CaseRead,
    CaseRiskLevel,
    CaseStatus,
    CaseUpdate,
)
from src.services.case_service import get_case, list_cases, update_case

router = APIRouter(tags=["cases"])


@router.get("", response_model=list[CaseRead])
async def list_cases_route(
    status: CaseStatus | None = None,
    risk_level: CaseRiskLevel | None = None,
    assigned_to: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[CaseRead]:
    return await list_cases(
        db=db,
        status=status,
        risk_level=risk_level,
        assigned_to=assigned_to,
    )


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
    return await update_case(db=db, case_id=case_id, payload=payload)