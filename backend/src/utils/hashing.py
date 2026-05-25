"""Hash sensitive identifiers (PAN tokens, emails)."""

from __future__ import annotations

import hashlib


def sha256_hex(value: str, *, salt: str = "") -> str:
    data = f"{salt}{value}".encode()
    return hashlib.sha256(data).hexdigest()
