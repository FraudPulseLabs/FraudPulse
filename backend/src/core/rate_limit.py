"""Per-IP rate limiting for public (unauthenticated) endpoints."""

from __future__ import annotations

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.core.config import get_optional_env

# Tuned to block casual abuse without interfering with Docker health checks.
LIMIT_ASSISTANT = get_optional_env("RATE_LIMIT_ASSISTANT", "10/minute") or "10/minute"
LIMIT_DEMO = get_optional_env("RATE_LIMIT_DEMO", "30/minute") or "30/minute"
LIMIT_ACCESS = get_optional_env("RATE_LIMIT_ACCESS", "5/minute") or "5/minute"
LIMIT_HEALTH = get_optional_env("RATE_LIMIT_HEALTH", "120/minute") or "120/minute"


def client_ip(request: Request) -> str:
    """Resolve the caller IP, honouring the nginx reverse proxy when present."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


limiter = Limiter(key_func=client_ip, default_limits=[])


def register_rate_limiting(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
