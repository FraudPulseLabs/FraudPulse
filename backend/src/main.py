import logging
from datetime import datetime, timezone

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.api.v1 import api_router
from src.core.constants import API_TITLE, API_VERSION
from src.core.logging import setup_logging
from src.core.rate_limit import LIMIT_HEALTH, limiter, register_rate_limiting
from src.db import session as db_session

logger = logging.getLogger(__name__)


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


@app.get("/health/db")
@limiter.limit(LIMIT_HEALTH)
def health_db(request: Request) -> JSONResponse:
    """Readiness probe: confirm Postgres actually answers.

    ``/health`` only proves the process is up, so an external monitor watching
    it reports "up" even while the database is unreachable. This opens a real
    connection and runs ``SELECT 1``, which lets a keyword monitor distinguish
    "API alive, database paused" from "everything fine" — the Supabase free
    tier pauses a project after roughly 7 days without activity, and the round
    trip doubles as the keep-alive that prevents it.

    Deliberately a sync handler: the SQLAlchemy engine here is the blocking
    driver, so FastAPI runs this in its threadpool rather than stalling the
    event loop for the duration of the query.
    """
    payload = {
        "status": "Running",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Mirrors src/db/session.py, where the engine stays None without DATABASE_URL.
    # Surfaced as 503 rather than 500: the app is healthy, its database is not.
    if db_session.engine is None:
        return JSONResponse(status_code=503, content={**payload, "database": "not_configured"})

    try:
        with db_session.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        logger.warning("Database readiness check failed: %s", exc)
        return JSONResponse(status_code=503, content={**payload, "database": "unreachable"})

    return JSONResponse(content={**payload, "database": "ok"})