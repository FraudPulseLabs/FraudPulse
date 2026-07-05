from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AccessRequestCreate(BaseModel):
    email: EmailStr = Field(..., max_length=320)
    company: str | None = Field(default=None, max_length=200)
    # Honeypot: hidden field that legitimate users leave blank. Bots that
    # blindly fill every input will populate it, letting us silently drop
    # the submission.
    website: str | None = Field(default=None, max_length=200)


class AccessRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    company: str | None
    status: str
    created_at: datetime


class AccessRequestResponse(BaseModel):
    success: bool
    message: str
    data: AccessRequestOut | None = None


class AccessRequestListResponse(BaseModel):
    success: bool
    message: str
    data: list[AccessRequestOut]


class AccessRequestApproveResponse(BaseModel):
    success: bool
    message: str
    data: AccessRequestOut | None = None
    # The freshly issued temporary password, returned once so the approver can
    # relay it to the user. Null when the user was already provisioned.
    temp_password: str | None = None
