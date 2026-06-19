from fastapi import APIRouter, Depends

from src.api.v1 import (
    access,
    admin,
    auth,
    cases_routes,
    alert_routes,
    decisions,
    demo,
    profiles_routes,
    scoring_routes,
    transactions,
    watchlist_routes,
)
from src.core.auth import get_current_user

api_router = APIRouter()

# Every route below requires a valid Supabase JWT, except the public /demo
# showcase endpoints which stay open so the model demo works unauthenticated.
_protected = [Depends(get_current_user)]

api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"], dependencies=_protected)
api_router.include_router(scoring_routes.router, prefix="/scoring", tags=["scoring"], dependencies=_protected)
api_router.include_router(decisions.router, prefix="/decisions", tags=["decisions"], dependencies=_protected)
api_router.include_router(alert_routes.router, prefix="/alerts", tags=["alerts"], dependencies=_protected)
api_router.include_router(cases_routes.router, prefix="/cases", tags=["cases"], dependencies=_protected)
api_router.include_router(watchlist_routes.router, prefix="/watchlist", tags=["watchlist"], dependencies=_protected)
api_router.include_router(profiles_routes.router, prefix="/profiles", tags=["profiles"], dependencies=_protected)
api_router.include_router(admin.router, prefix="/admin", tags=["admin"], dependencies=_protected)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"], dependencies=_protected)

# Public — no authentication required.
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
api_router.include_router(access.router, prefix="/access", tags=["access"])

__all__ = ["api_router"]