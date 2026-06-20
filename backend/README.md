# Backend

FastAPI backend for the payment fraud detection system. It exposes API routes for transactions, scoring, decisions, alerts, cases, watchlists, profiles, and admin operations. It also keeps the ML data pipeline code under `ml/`.

## Quick Start

Run these commands from the `backend/` directory:

```bash
pip install -r requirements.txt
python run.py
```

After the server starts:

- Health check: `GET http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
- ReDoc docs: `http://localhost:8000/redoc`

All versioned API routes are mounted under:

```text
/api/v1
```

## Configuration

Create a local `.env` file in this directory. You can start from `.env.example`.

```bash
cp .env.example .env
```

Set `DATABASE_URL` to your Supabase or local Postgres connection string:

```text
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres?sslmode=require
```

Notes:

- Use the `postgresql+psycopg://` prefix because the backend uses SQLAlchemy with psycopg v3.
- If `DATABASE_URL` is missing, database sessions are not configured, but the app can still start and serve routes that do not need the database.
- Keep `.env` local. Do not commit real database passwords or Supabase secrets.

## API Structure

The app is created in `src/main.py`. It includes the versioned router from `src/api/v1/__init__.py`.

Current route modules:

- `transactions.py` — `POST /transactions` runs the full ingest pipeline (merchant-blacklist short-circuit → card-history build → in-process scoring → threshold-mapped decision → persist `transactions` + `fraud_scores` + optional `score_reasons`). `?explain=true` returns SHAP contributions. `GET /transactions` lists the most recent rows. See `src/services/decision_service.py` for the wiring and `src/schemas/transaction_ingest.py` for the request/response shapes.
- `scoring.py` — fraud score requests.
- `decisions.py` — decision workflow stubs.
- `alerts.py` — fraud alert endpoints.
- `cases.py` — investigation case endpoints.
- `watchlist.py` — watchlist endpoints.
- `profiles.py` — profile endpoints.
- `admin.py` — admin/settings endpoints.

## Database

Database connection setup lives in `src/db/session.py`.

SQLAlchemy models live in `src/db/models/`. They are aligned with the Supabase `public` schema documented in the repo root `supabase-db` file:

- UUID primary keys where Supabase uses `uuid`.
- Matching table names such as `audit_log`, `watchlist`, and `transactions`.
- PostgreSQL types such as `JSONB`, `Numeric`, `Date`, and timezone-aware timestamps.

The `transactions` table was aligned with the data-science 20-column view on
2026-05-31 by adding three nullable columns: `transaction_type`,
`transaction_country`, and `is_fraud`. `is_fraud` is the **ground-truth label**
and is intentionally never written by the ingest path — it is reserved for
review/backfill workflows. The live routing decision lives in the separate
`decision` column (`APPROVE` / `APPROVE_WITH_REVIEW` / `DECLINE`). The DDL
script is `scripts/apply_alignment.py` (idempotent; uses `ADD COLUMN IF NOT
EXISTS`). Verify drift with `scripts/verify_models_vs_db.py`.

Pydantic schemas live in `src/schemas/` and describe the JSON shapes used by the API.

## ML Pipeline

ML and dataset code lives in `ml/`.

Important files:

- `ml/preprocessing.py` — dataset splitting, encoding, and cleanup helpers.
- `ml/feature_engineering.py` — transaction feature creation.
- `ml/data_exploration.py` — exploratory analysis and exports.
- `ml/dataset_generator.py` — dataset generation utilities.

ML modules continue to support:

```python
from src.config import DATA_DIR
```

This keeps dataset paths stable while the FastAPI app uses the newer `src/core/config.py` layout.

## Tests

Run the backend test suite from the `backend/` directory:

```bash
pytest
```

Test layout:

- `tests/conftest.py` — shared JWT auth fixtures for route integration tests
- `tests/unit/` — service logic, ML preprocessing, scoring, decision ingest, alerts/cases/watchlist CRUD
- `tests/integration/` — `/health`, auth gates, and ops API routes (alerts, cases, watchlist)

Most tests mock the database and model artefacts, so the suite runs without a live Supabase connection.

## Useful Files

- `run.py` — development server entrypoint.
- `src/main.py` — FastAPI app setup.
- `src/core/config.py` — environment variables and project paths.
- `src/db/session.py` — database engine/session setup.
- `scripts/seed.py` — placeholder for future seed data.
- `BACKEND_FILES_EXPLAINED.txt` — beginner-friendly file-by-file backend guide.
