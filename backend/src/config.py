"""Backward-compatible exports for `from src.config import DATA_DIR` (e.g. ML modules)."""

from src.core.config import (
    BASE_DIR,
    DATA_DIR,
    PROJECT_ROOT,
    get_env,
    ML_ARTEFACTS_DIR,
)

__all__ = ["BASE_DIR", "DATA_DIR", "PROJECT_ROOT", "get_env", "ML_ARTEFACTS_DIR"]
