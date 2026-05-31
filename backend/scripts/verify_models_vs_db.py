"""
Read-only check: compare each SQLAlchemy model's columns against the live
Supabase schema. Flags:
  - model-only columns  -> NOT in the DB; any SELECT/INSERT using them breaks.
  - live-only columns   -> DB columns the model doesn't map (informational).

Usage (from repo root or anywhere):  python backend/scripts/verify_models_vs_db.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from src.db import models as m  # noqa: E402

engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
insp = inspect(engine)

classes = [
    m.Alert, m.AuditLog, m.Case, m.CaseEvent, m.CaseNote, m.FraudScore,
    m.Profile, m.RejectedRequest, m.RuleTrigger, m.ScoreReason, m.SystemConfig,
    m.Transaction, m.TransactionLifecycle, m.Watchlist, m.WatchlistHistory,
]

live_tables = set(insp.get_table_names(schema="public"))
problems = 0

for cls in classes:
    table = cls.__tablename__
    model_cols = {c.name for c in cls.__table__.columns}
    if table not in live_tables:
        print(f"[MISSING TABLE] {table} not found in live public schema")
        problems += 1
        continue
    live_cols = {c["name"] for c in insp.get_columns(table, schema="public")}
    model_only = model_cols - live_cols
    live_only = live_cols - model_cols
    status = "DRIFT" if model_only else "OK"
    print(f"[{status}] {table}: model={len(model_cols)} live={len(live_cols)}")
    if model_only:
        print(f"    model-only (NOT in DB -> breaks queries): {sorted(model_only)}")
        problems += 1
    if live_only:
        print(f"    live-only (DB cols not mapped by model):  {sorted(live_only)}")

print()
print("RESULT:", "ALL MODELS SAFE (no model-only columns)" if problems == 0
      else f"{problems} table(s) need attention")
