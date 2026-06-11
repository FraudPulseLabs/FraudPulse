"""Schemas for the authenticated user and the /auth/me response."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class AuthUser(BaseModel):
    """The identity extracted from a verified Supabase JWT."""

    id: uuid.UUID
    email: str | None = None


class ProfileInfo(BaseModel):
    """The app-level profile row joined to the auth user."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    full_name: str
    is_active: bool


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str | None = None
    profile: ProfileInfo | None = None
