# Architecture and Tech Stack

## High-level architecture

FraudPulse is a two-tier application: an Angular single-page dashboard talks to
a FastAPI backend over a REST API. The backend performs feature extraction,
runs the rule engine and the machine-learning model, persists results, and
serves data to the dashboard. A managed Postgres database stores all
transactional and operational data.

## Backend

- **Framework**: FastAPI (Python).
- **Server**: Uvicorn ASGI server.
- **Hosting**: deployed on Oracle Cloud Infrastructure (OCI) as a Docker
  container.
- **Responsibilities**: transaction ingestion, real-time feature building,
  rule evaluation, model scoring, decisioning, alerts, cases, watchlists, and
  the audit trail.

The backend exposes the REST API described in the API Reference and verifies
Supabase-issued JWTs on protected routes.

## Frontend

- **Framework**: Angular 20.
- **Styling**: Tailwind CSS.
- **Hosting**: deployed on Render as a static site.
- **Responsibilities**: the analyst dashboard for monitoring transactions,
  investigating alerts and cases, managing watchlists, and the public model
  demo.

## Data and storage

- **Database**: PostgreSQL, provided through Supabase.
- **ORM**: SQLAlchemy.
- **Migrations**: Alembic.

Transactions, scores, score reasons, rule triggers, decisions, alerts, cases,
watchlists, and audit logs are all stored in Postgres.

## Authentication

Authentication is handled by Supabase Auth, which mints JSON Web Tokens (JWTs)
on the frontend. The backend does not issue tokens; it verifies them using the
Supabase project's public JWKS. This keeps auth stateless and offloads
credential management to Supabase.

## Machine learning stack

- **Model**: LightGBM gradient-boosted trees, calibrated to output
  probabilities.
- **Libraries**: scikit-learn for calibration and preprocessing, pandas and
  NumPy for data handling, joblib for model persistence.
- Model artefacts are versioned and loaded by the scoring service at runtime.

## Assistant (RAG) subsystem

The landing-page assistant is powered by a retrieval-augmented-generation (RAG)
pipeline in the backend. It embeds a curated corpus of FraudPulse documentation
with a local sentence-transformers model, stores the vectors in a FAISS index,
retrieves the most relevant chunks for a question, and uses a Groq-hosted large
language model to generate a grounded, cited answer. The assistant answers only
from the documentation and refuses out-of-scope questions.

## Deployment and CI/CD

- The backend is containerized with Docker and deployed to Oracle Cloud.
- The frontend is built and deployed to Render.
- Continuous integration runs backend tests (pytest) and frontend tests (Jest)
  on every pull request.
- A deployment workflow builds and ships the backend image after CI passes on
  the main branch.
