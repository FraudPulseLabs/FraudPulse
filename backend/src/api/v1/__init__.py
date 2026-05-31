from src.api.v1 import scoring_routes
from src.api.v1 import watchlist_routes
from fastapi import APIRouter

from src.api.v1 import admin, alerts, cases, decisions, demo, metrics, profiles, transactions

api_router = APIRouter()
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])
api_router.include_router(scoring_routes.router, prefix="/scoring", tags=["scoring"])
api_router.include_router(decisions.router, prefix="/decisions", tags=["decisions"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(watchlist_routes.router, prefix="/watchlist", tags=["watchlist"])
api_router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])

__all__ = ["api_router"]
