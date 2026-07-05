import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.core.auth import require_admin
from src.core.rate_limit import LIMIT_ACCESS, limiter
from src.core.supabase_admin import SupabaseAdminError, SupabaseConfigError
from src.db.session import get_db
from src.schemas.access_request import (
    AccessRequestApproveResponse,
    AccessRequestCreate,
    AccessRequestListResponse,
    AccessRequestOut,
    AccessRequestResponse,
)
from src.services.access_request_service import (
    AccessRequestNotFound,
    approve_access_request,
    client_ip,
    list_access_requests,
    submit_access_request,
)

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
    # Always return a success message so that honeypot hits and duplicate
    # submissions can't be distinguished from legitimate ones by the caller.
    return AccessRequestResponse(
        success=True,
        message="Your access request has been received. Our team will be in touch shortly.",
        data=AccessRequestOut.model_validate(record) if record is not None else None,
    )


@router.get(
    "/requests",
    response_model=AccessRequestListResponse,
    dependencies=[Depends(require_admin)],
)
async def list_access_request_records(
    db: Session = Depends(get_db),
) -> AccessRequestListResponse:
    records = await list_access_requests(db)
    return AccessRequestListResponse(
        success=True,
        message="Access requests retrieved successfully.",
        data=[AccessRequestOut.model_validate(r) for r in records],
    )


@router.post(
    "/requests/{request_id}/approve",
    response_model=AccessRequestApproveResponse,
    dependencies=[Depends(require_admin)],
)
async def approve_access_request_record(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> AccessRequestApproveResponse:
    """Approve a pending request: provision the user in Supabase Auth and mark
    the record approved so they can sign in."""
    try:
        result = await approve_access_request(db, request_id)
    except AccessRequestNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Access request not found.",
        )
    except SupabaseConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except SupabaseAdminError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not provision the user in Supabase: {exc}",
        )

    if result.already_approved:
        message = "This request was already approved."
    elif result.user_existed:
        message = (
            f"{result.record.email} already had a Supabase account; "
            "the request is now marked approved."
        )
    else:
        message = (
            f"Approved. {result.record.email} can now sign in with the issued password."
        )

    return AccessRequestApproveResponse(
        success=True,
        message=message,
        data=AccessRequestOut.model_validate(result.record),
        temp_password=result.temp_password,
    )

