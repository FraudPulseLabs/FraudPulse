"""Security helpers (API keys, hashing passwords for admin, etc.)."""

from __future__ import annotations

import hmac
import secrets
def compare_digest(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def generate_token_hex(nbytes: int = 32) -> str:
    return secrets.token_hex(nbytes)
