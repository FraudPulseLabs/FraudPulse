# Architecture and Tech Stack

## High-level architecture

FraudPulse is a modular full-stack application:

```text
Angular frontend (Render)  →  FastAPI backend (Oracle Cloud / DuckDNS)  →  Supabase Postgres
                                      │
                         ┌────────────┼────────────┐
                         ▼            ▼            ▼
                    ML engine    RAG assistant   Analytics
                   (primary)      (support)
```

The **ML fraud engine is the primary decision layer**. The RAG assistant is a
secondary support capability for documentation questions on the landing page.

## Backend

| Component | Technology |
| --- | --- |
| Framework | FastAPI (Python 3.11+) |
| Server | Uvicorn ASGI |
| Hosting | Docker on Oracle Cloud Infrastructure (OCI) |
| Public URL | `fraudpulse.duckdns.org` |
| ORM | SQLAlchemy models aligned with Supabase Postgres schema |

**Responsibilities:** transaction ingestion, real-time feature building, rule
evaluation, ML scoring, decisioning, alerts, cases, watchlists, audit trail,
and the public assistant endpoint.

Backend code is organized in layers: API routes → services → SQLAlchemy models.

## Frontend

| Component | Technology |
| --- | --- |
| Framework | Angular 21 |
| Styling | Tailwind CSS v4 |
| Hosting | Render (static site from `render.yaml`) |
| Public URL | `https://fraudpulse-u2va.onrender.com/` |

**Responsibilities:** analyst dashboard (overview, transactions, alerts, cases,
watchlist), authentication via Supabase, public landing page with model demo
and chatbot widget.

Routes use lazy loading and auth guards (`authGuard`, `guestGuard`).

## Data and storage

- **Database:** PostgreSQL via Supabase
- **Connection:** `DATABASE_URL` with `postgresql+psycopg://` driver prefix
- **Stored entities:** transactions, fraud scores, score reasons, rule triggers,
  decisions, alerts, cases, watchlists, watchlist history, audit logs

## Authentication

**Supabase Auth** mints JWTs on the frontend. The backend verifies tokens using
the project's public JWKS (asymmetric keys). The backend does not store passwords
or issue its own sessions.

## Machine learning stack

| Component | Detail |
| --- | --- |
| Model | Calibrated LightGBM (`fraud_model.pkl`) |
| Libraries | scikit-learn, LightGBM, pandas, NumPy |
| Inference | Loaded once per process via the scoring service |
| Outputs | Fraud probability 0–1, mapped to APPROVE / APPROVE_WITH_REVIEW / DECLINE |

## RAG assistant stack

| Component | Detail |
| --- | --- |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`) |
| Vector store | FAISS (cosine similarity) |
| Generation | Groq-hosted LLM (`llama-3.3-70b-versatile` by default) |
| Corpus | Curated Markdown docs in `backend/rag/docs/` |

Pipeline: retrieve → relevance gate → generate → validate → cite. Refuses
out-of-corpus questions below the relevance threshold.

## Deployment and CI/CD

| Layer | How it deploys |
| --- | --- |
| Frontend | Render static build (`npm run build:prod`) |
| Backend | Docker image to GHCR; deployed to OCI via GitHub Actions on `main` |
| CI | pytest (backend), Jest (frontend), RAG index smoke test on every PR |

Secrets (`DATABASE_URL`, `GROQ_API_KEY`) are injected via environment variables,
never committed to source control.
