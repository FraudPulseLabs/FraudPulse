from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.supabase_admin import UserAlreadyExists, create_auth_user
from src.db.models.access_request import AccessRequest
from src.schemas.access_request import AccessRequestCreate


class AccessRequestNotFound(Exception):
    """Raised when an access request id does not resolve to a record."""


@dataclass
class ApprovalResult:
    record: AccessRequest
    temp_password: str | None
    already_approved: bool
    user_existed: bool


async def submit_access_request(
    db: Session,
    payload: AccessRequestCreate,
    source_ip: str | None,
) -> tuple[AccessRequest | None, bool]:
    """Persist a new access request. Returns (record, created).

    If the honeypot ``website`` field is populated, we treat the submission
    as bot traffic: no database write happens and ``(None, False)`` is
    returned so the caller can still respond with a success payload.
    """
    if payload.website and payload.website.strip():
        return None, False

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


def _generate_temp_password() -> str:
    """A strong, URL-safe temporary password (~16 chars) comfortably above
    Supabase's minimum-length policy."""
    return secrets.token_urlsafe(12)


async def approve_access_request(db: Session, request_id: uuid.UUID) -> ApprovalResult:
    """Approve a pending access request.

    Provisions the requester in Supabase Auth (pre-confirmed, with a freshly
    issued temporary password) and flips the record's status to ``approved`` so
    they can sign in. Idempotent: re-approving an already-approved request is a
    no-op.

    Raises:
        AccessRequestNotFound: when ``request_id`` has no matching record.
        SupabaseConfigError / SupabaseAdminError: propagated from provisioning.
    """
    record = db.get(AccessRequest, request_id)
    if record is None:
        raise AccessRequestNotFound(str(request_id))

    if record.status == "approved":
        return ApprovalResult(
            record=record, temp_password=None, already_approved=True, user_existed=False
        )

    password: str | None = _generate_temp_password()
    user_existed = False
    try:
        await create_auth_user(record.email, password)
    except UserAlreadyExists:
        # The email already has a Supabase account — approve the request without
        # issuing (and exposing) a new password.
        password = None
        user_existed = True

    record.status = "approved"
    db.commit()
    db.refresh(record)
    return ApprovalResult(
        record=record,
        temp_password=password,
        already_approved=False,
        user_existed=user_existed,
    )


async def list_access_requests(db: Session) -> list[AccessRequest]:
    """Return every access request, newest first."""
    return list(
        db.scalars(
            select(AccessRequest).order_by(AccessRequest.created_at.desc())
        ).all()
    )


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client:
        return request.client.host
    return None

