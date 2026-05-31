"""
backend/scripts/apply_alignment.py

Additive alignment of the live `transactions` table with the data-science /
training-CSV view. Adds three NULLABLE columns (idempotent — safe to re-run):

    transaction_type     TEXT     -- scorer field, was body-only until now
    transaction_country  TEXT     -- scorer field, was body-only until now
    is_fraud             BOOLEAN  -- GROUND-TRUTH label, NOT the live decision.
                                     Never written by the ingest/scoring path;
                                     populated later by review / chargeback backfill.

Deliberately NOT done (see discussion): no rename of `id` -> `transaction_id`
(PK referenced by 4 FK tables + frontend) or `ts` -> `timestamp` (3 indexes).
Those names are mapped at the API/serialization boundary instead.

Usage (from the backend/ directory):
    python scripts/apply_alignment.py

Only ADD COLUMN IF NOT EXISTS — additive and reversible (DROP COLUMN undoes it).
After running, confirm model == DB with:
    python scripts/verify_models_vs_db.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "")
PLACEHOLDER_MARKERS = ("YOUR_PASSWORD", "YOUR_PROJECT_REF", "YOUR_REGION")


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


if not DATABASE_URL:
    fail("DATABASE_URL is empty. Fill backend/.env with your Supabase connection string.")
if any(marker in DATABASE_URL for marker in PLACEHOLDER_MARKERS):
    fail("DATABASE_URL still contains placeholders — replace them in backend/.env.")

DDL = """
ALTER TABLE public.transactions
    ADD COLUMN IF NOT EXISTS transaction_type    TEXT,
    ADD COLUMN IF NOT EXISTS transaction_country TEXT,
    ADD COLUMN IF NOT EXISTS is_fraud            BOOLEAN;

COMMENT ON COLUMN public.transactions.is_fraud IS
    'Ground-truth fraud label for re-training. NULL at ingest; set later by '
    'review/chargeback backfill. Distinct from the decision column.';
"""

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def transactions_columns() -> set[str]:
    return {c["name"] for c in inspect(engine).get_columns("transactions", schema="public")}


before = transactions_columns()
print(f"transactions columns before: {len(before)}")

with engine.begin() as conn:
    conn.execute(text(DDL))

after = transactions_columns()
added = sorted(after - before)
print(f"transactions columns after:  {len(after)}")
print(f"added: {added if added else '(none — already present, idempotent no-op)'}")

for required in ("transaction_type", "transaction_country", "is_fraud"):
    mark = "OK" if required in after else "MISSING"
    print(f"  [{mark}] {required}")
