"""Seed reference data / demo rows when DATABASE_URL is configured."""

from __future__ import annotations

from src.core.config import DATABASE_URL


def main() -> None:
    if not DATABASE_URL:
        print("DATABASE_URL not set; skipping seed.")
        return
    print("Run: python -m scripts.seed_ops_data  (alerts, cases, watchlist)")
    print("Run: python -m scripts.seed_demo_transactions  (model demo fixture)")


if __name__ == "__main__":
    main()
