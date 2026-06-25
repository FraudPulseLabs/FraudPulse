# FraudPulse — Deployment Guide

## 1. Overview

FraudPulse is a full-stack fraud detection platform for card payments. It ingests transactions, scores risk with ML, and classifies outcomes as **ALLOW**, **REVIEW**, or **BLOCK**. Production deployments serve the analyst dashboard and public API from separate hosts behind a modular, service-oriented layout.

## 2. Live Deployment

| Service | URL |
| --- | --- |
| Frontend | [https://fraudpulse-u2va.onrender.com/](https://fraudpulse-u2va.onrender.com/) |
| Backend (API docs) | [https://fraudpulse.duckdns.org/docs](https://fraudpulse.duckdns.org/docs) |
| Backend (health) | [https://fraudpulse.duckdns.org/health](https://fraudpulse.duckdns.org/health) |

## 3. Architecture

```text
Angular Frontend (Render)
        │
        ▼
FastAPI Backend (Oracle Cloud / DuckDNS)
        │
   ┌────┼────┬────────────┐
   ▼    ▼    ▼            ▼
  ML   RAG  Analytics   Supabase
```

- **Frontend** — Angular SPA; calls the backend via `apiUrl` in `frontend/src/environments/`.
- **Backend** — FastAPI (`/api/v1`); fraud scoring, decisions, cases, and RAG assistant.
- **Data** — Supabase Postgres via `DATABASE_URL`.
- **ML** — In-process scoring and decisioning (primary intelligence layer).
- **RAG** — Secondary support assistant; Groq LLM + indexed knowledge base.

## 4. Running Locally

### Frontend

```bash
cd frontend
npm ci
npx ng serve       # http://localhost:4200
```

Alternatively: `npm start` (alias for `ng serve`).

Production build: `npm run build:prod`

### Backend

Requires **Python 3.11 or 3.12**:

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt -r requirements-rag.txt
python run.py      # http://localhost:8000
```

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

### Environment variables

A `backend/.env` file is **required** for full functionality. Copy the template:

```bash
cp .env.example .env   # run from backend/
```

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | Supabase/Postgres connection (`postgresql+psycopg://…`) |
| `GROQ_API_KEY` | RAG assistant LLM (optional locally; required for chat responses) |
| `GROQ_MODEL` | LLM override (default: `llama-3.3-70b-versatile`) |

Do not commit `.env`. Frontend env files hold **public** config only (`apiUrl`, etc.).

## 5. Cloud Deployment

### Frontend — Render

- Defined in `render.yaml` (static site, `frontend/` root).
- Build: `npm ci && npm run build:prod`
- Publish path: `dist/fraudpulse/browser`
- SPA rewrites route all paths to `index.html`.

### Backend — Oracle Cloud + DuckDNS

- Docker image built from `backend/Dockerfile` (includes ML + RAG index).
- Hosted on Oracle Cloud Infrastructure (OCI); exposed at `fraudpulse.duckdns.org`.
- Container listens on port `8000`; health check at `/health`.
- Secrets (`DATABASE_URL`, `GROQ_API_KEY`) are injected at deploy time — never committed.

### CI/CD

| Workflow | Trigger | Action |
| --- | --- | --- |
| `ci.yml` | Push to `main`, PRs | Backend pytest, frontend tests/lint, RAG smoke checks |
| `deploy.yml` | CI success on `main` | Build/push backend image to GHCR; deploy to OCI via SSH |

Render frontend deploys are configured separately via the Render dashboard / `render.yaml`.

## 6. Notes

- **Production-first** — treat `DATABASE_URL` and `GROQ_API_KEY` as secrets in all environments.
- **Modular design** — frontend, API, ML engine, and RAG assistant are independently deployable components sharing a common API contract.
- **ML over RAG** — fraud decisioning is driven by the ML pipeline; the assistant is a support layer only.
- **Branch protection** — changes merge to `main` via PR with passing CI; backend auto-deploys after CI succeeds.

**See also:** [README.md](README.md) · [design-and-evaluation.md](design-and-evaluation.md) · [ai-tooling.md](ai-tooling.md)
