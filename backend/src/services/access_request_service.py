from __future__ import annotations

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.db.models.access_request import AccessRequest
from src.schemas.access_request import AccessRequestCreate


async def submit_access_request(
    db: Session,
    payload: AccessRequestCreate,
    source_ip: str | None,
) -> tuple[AccessRequest, bool]:
    """Persist a new access request. Returns (record, created)."""
    normalized_email = payload.email.strip().lower()
    company = payload.company.strip() if payload.company else None

    existing = db.scalar(
        select(AccessRequest).where(func.lower(AccessRequest.email) == normalized_email)
    )
    if existing is not None:
        return existing, False

    record = AccessRequest(
        email=normalized_email,
        company=company,
        source_ip=source_ip,
        status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record, True


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None
