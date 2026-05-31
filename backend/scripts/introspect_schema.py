"""
backend/scripts/introspect_schema.py

Read-only introspection of the live database pointed at by DATABASE_URL
(loaded from backend/.env). Dumps every table in the `public` schema:
columns, types, nullability, defaults, primary keys, foreign keys, unique
constraints, indexes, plus any Postgres enum types.

Usage (from the backend/ directory):
    python scripts/introspect_schema.py

Writes the report to backend/schema_introspection.txt and prints it.
This script ONLY reads catalog metadata — it never modifies the database.
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
if any(m in DATABASE_URL for m in PLACEHOLDER_MARKERS):
    fail(
        "DATABASE_URL still contains placeholders (YOUR_PASSWORD / YOUR_PROJECT_REF / "
        "YOUR_REGION). Replace them with real values in backend/.env."
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
insp = inspect(engine)

lines: list[str] = []


def out(s: str = "") -> None:
    lines.append(s)


SCHEMA = "public"
tables = sorted(insp.get_table_names(schema=SCHEMA))
out(f"# Schema introspection — schema='{SCHEMA}', {len(tables)} tables")
out("")

for t in tables:
    out(f"## {t}")
    pk = insp.get_pk_constraint(t, schema=SCHEMA)
    pk_cols = set(pk.get("constrained_columns") or [])

    for col in insp.get_columns(t, schema=SCHEMA):
        name = col["name"]
        typ = str(col["type"])
        nullable = "NULL" if col["nullable"] else "NOT NULL"
        default = col.get("default")
        flags = []
        if name in pk_cols:
            flags.append("PK")
        if default is not None:
            flags.append(f"default={default}")
        extra = ("  [" + ", ".join(flags) + "]") if flags else ""
        out(f"  - {name}: {typ} {nullable}{extra}")

    for fk in insp.get_foreign_keys(t, schema=SCHEMA):
        out(
            f"  FK: {fk.get('constrained_columns')} -> "
            f"{fk.get('referred_schema') or SCHEMA}.{fk.get('referred_table')}"
            f"{fk.get('referred_columns')}"
        )
    for uq in insp.get_unique_constraints(t, schema=SCHEMA):
        out(f"  UNIQUE: {uq.get('column_names')}")
    for ix in insp.get_indexes(t, schema=SCHEMA):
        out(
            f"  INDEX: {ix.get('name')} cols={ix.get('column_names')} "
            f"unique={ix.get('unique')}"
        )
    out("")

enum_sql = text(
    """
    select t.typname as enum_name, e.enumlabel as value
    from pg_type t
    join pg_enum e on t.oid = e.enumtypid
    join pg_namespace n on n.oid = t.typnamespace
    where n.nspname = :schema
    order by enum_name, e.enumsortorder
    """
)
with engine.connect() as conn:
    enum_rows = conn.execute(enum_sql, {"schema": SCHEMA}).fetchall()

if enum_rows:
    out("## Postgres enum types")
    current = None
    for enum_name, value in enum_rows:
        if enum_name != current:
            out(f"  {enum_name}:")
            current = enum_name
        out(f"    - {value}")
    out("")

report = "\n".join(lines)
out_path = BACKEND_DIR / "schema_introspection.txt"
out_path.write_text(report, encoding="utf-8")
print(report)
print(f"\n[written to {out_path}]")
