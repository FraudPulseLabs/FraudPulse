from __future__ import annotations
from datetime import datetime, timezone

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.v1 import api_router
from src.core.constants import API_TITLE, API_VERSION
from src.core.logging import setup_logging
from src.api.v1.watchlist_routes import router as watchlist_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    yield


app = FastAPI(title=API_TITLE, version=API_VERSION, lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")
app.include_router(watchlist_router, prefix="/api/v1")

@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "Running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
