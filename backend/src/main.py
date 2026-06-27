from __future__ import annotations
from datetime import datetime, timezone

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import api_router
from src.core.constants import API_TITLE, API_VERSION
from src.core.logging import setup_logging
from src.core.rate_limit import LIMIT_HEALTH, limiter, register_rate_limiting


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    yield


app = FastAPI(title=API_TITLE, version=API_VERSION, lifespan=lifespan)
register_rate_limiting(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://fraudpulse-u2va.onrender.com",
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
@limiter.limit(LIMIT_HEALTH)
async def health(request: Request) -> dict[str, str]:
    return {
        "status": "Running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }