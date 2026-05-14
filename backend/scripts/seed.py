"""Seed reference data / demo rows when DATABASE_URL is configured."""

from __future__ import annotations

from src.core.config import DATABASE_URL


def main() -> None:
    if not DATABASE_URL:
        print("DATABASE_URL not set; skipping seed.")
        return
    print("Seed stub: create tables and insert demo rows via Alembic/SQLAlchemy here.")


if __name__ == "__main__":
    main()
