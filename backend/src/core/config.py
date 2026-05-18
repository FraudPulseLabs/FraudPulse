"""Application configuration and paths."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # src/
PROJECT_ROOT = BASE_DIR.parent                     # backend/
DATA_DIR = PROJECT_ROOT / "data"

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