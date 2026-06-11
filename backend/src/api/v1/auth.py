"""Authentication routes.

Login/logout happen client-side against Supabase Auth, so the backend exposes
only a `/me` endpoint that echoes the verified caller and their profile row.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.auth import get_current_user
from src.db.models.profile import Profile
from src.db.session import get_db
from src.schemas.auth import AuthUser, MeResponse, ProfileInfo

router = APIRouter()


@router.get("/me", response_model=MeResponse)
async def me(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MeResponse:
    profile = db.get(Profile, current_user.id)
    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        profile=ProfileInfo.model_validate(profile) if profile else None,
    )
