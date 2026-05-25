"""GeoIP lookups (wire to MaxMind or provider when integrated)."""

from __future__ import annotations


def country_from_ip(ip_address: str | None) -> str | None:
    if not ip_address:
        return None
    return None
