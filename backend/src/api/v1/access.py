from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.core.rate_limit import LIMIT_ACCESS, limiter
from src.db.session import get_db
from src.schemas.access_request import AccessRequestCreate, AccessRequestResponse
from src.services.access_request_service import client_ip, submit_access_request

router = APIRouter(tags=["Access"])


@router.post("/requests", response_model=AccessRequestResponse, status_code=201)
@limiter.limit(LIMIT_ACCESS)
async def create_access_request(
    request: Request,
    payload: AccessRequestCreate,
    db: Session = Depends(get_db),
) -> AccessRequestResponse:
    record, _created = await submit_access_request(
        db=db,
        payload=payload,
        source_ip=client_ip(request),
    )
    return AccessRequestResponse(
        success=True,
        message="Your access request has been received. Our team will be in touch shortly.",
        data=record,
    )
