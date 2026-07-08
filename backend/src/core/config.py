"""Application configuration and paths."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # src/
PROJECT_ROOT = BASE_DIR.parent                     # backend/
DATA_DIR = PROJECT_ROOT / "ml" /"data"
ML_ARTEFACTS_DIR = PROJECT_ROOT / "ml" / "artefacts" / "version2"

load_dotenv(PROJECT_ROOT / ".env")


def get_env(key: str, default: str | None = None) -> str:
    value = os.getenv(key, default)
    if value is None:
        raise ValueError(f"Missing required environment variable: {key}")
    return value


def get_optional_env(key: str, default: str | None = None) -> str | None:
    return os.getenv(key, default)


DATABASE_URL: str = get_env("DATABASE_URL")
API_V1_PREFIX: str = "/api/v1"


# ---- Supabase Auth (JWT verification) ---------------------------------------
# The backend does NOT issue tokens; it only verifies the JWT minted by Supabase
# Auth (GoTrue) on the frontend. Verification uses the project's public JWKS
# (asymmetric ES256/RS256 keys — the modern Supabase default).


def _derive_supabase_url() -> str | None:
    """Project URL for token verification.

    Prefers an explicit SUPABASE_URL; otherwise derives it from the Supabase
    pooler username in DATABASE_URL (``postgres.<project_ref>``) so no extra
    env config is needed for typical Supabase setups.
    """
    explicit = get_optional_env("SUPABASE_URL")
    if explicit:
        return explicit.rstrip("/")
    try:
        parsed = urlparse(DATABASE_URL)
        user = parsed.username or ""
        host = parsed.hostname or ""
        if user.startswith("postgres.") and "pooler.supabase.com" in host:
            ref = user.split("postgres.", 1)[1]
            if ref:
                return f"https://{ref}.supabase.co"
    except Exception:
        pass
    return None


SUPABASE_URL: str | None = _derive_supabase_url()
SUPABASE_JWKS_URL: str | None = (
    f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else None
)
SUPABASE_JWT_AUD: str = "authenticated"
# Optional legacy fallback: set this to verify HS256-signed tokens with the
# shared "JWT Secret" instead of the JWKS asymmetric keys. Leave unset to use JWKS.
SUPABASE_JWT_SECRET: str | None = get_optional_env("SUPABASE_JWT_SECRET")

# Service-role key — grants the backend the Supabase Auth *admin* API (creating
# users when an access request is approved). This is a privileged secret that
# must NEVER be exposed to the browser; it lives only in the backend .env.
SUPABASE_SERVICE_ROLE_KEY: str | None = get_optional_env("SUPABASE_SERVICE_ROLE_KEY")

# The single admin account allowed to view and approve access requests. Override
# via ADMIN_EMAIL in .env; defaults to the FraudPulse analyst account.
ADMIN_EMAIL: str = get_optional_env("ADMIN_EMAIL", "analyst@fraudpulse.io") or "analyst@fraudpulse.io"