# FraudPulse — Design & Evaluation

This document describes the software and architecture patterns used in FraudPulse, the rationale behind them, and the testing strategy applied across the stack.

---

## 1. Design Overview

FraudPulse is a modular full-stack fraud detection platform. The system is split into independently deployable layers:

- **Angular frontend** — analyst dashboard and landing experience
- **FastAPI backend** — REST API, business logic, and orchestration
- **ML engine** — real-time fraud scoring and decisioning (primary intelligence)
- **RAG assistant** — secondary support layer for product guidance
- **Supabase Postgres** — persistent data store

Design priorities: **separation of concerns**, **testability**, **clear API contracts**, and **ML-first decisioning** with RAG as a support capability only.

---

## 2. Architecture Patterns

### 2.1 Layered Architecture

The backend follows a classic layered structure:

```text
API routes (FastAPI)  →  Services  →  Data models (SQLAlchemy)  →  Postgres
```

| Layer | Location | Responsibility |
| --- | --- | --- |
| API | `backend/src/api/v1/` | HTTP routing, request validation, auth dependencies |
| Services | `backend/src/services/` | Business logic, orchestration, ML invocation |
| Schemas | `backend/src/schemas/` | Pydantic DTOs for request/response contracts |
| Models | `backend/src/db/models/` | SQLAlchemy ORM entities aligned with Supabase schema |
| ML | `backend/ml/` | Training scripts, feature engineering, model artefacts |

**Why:** Keeps HTTP concerns separate from domain logic and persistence. Services can be unit-tested without spinning up a web server or database.

### 2.2 API Versioning

All versioned routes are mounted under `/api/v1` in `backend/src/main.py`.

**Why:** Allows future breaking changes under `/api/v2` without disrupting existing clients. The frontend targets a single `apiUrl` per environment.

### 2.3 Service Layer Pattern

Core workflows are encapsulated in dedicated services:

- `decision_service.py` — transaction ingest pipeline
- `scoring_service.py` — ML inference and SHAP explanations
- `alert_service.py`, `case_service.py`, `watchlist_service.py` — operational workflows
- `rule_engine.py` — declarative rule evaluation (velocity, geo, amount)

**Why:** Routes stay thin; reusable logic lives in one place. The ingest pipeline composes multiple services in a predictable order.

### 2.4 Pipeline Pattern (Transaction Ingest)

A submitted transaction flows through a fixed pipeline:

```text
Validate request → Watchlist check → Build card history → Feature engineering
    → ML scoring → Threshold mapping → Persist (transaction + score + reasons)
    → Emit events (alerts/cases as needed)
```

Implemented in `decision_service.py` with `scoring_service` and `watchlist_service`.

**Why:** Fraud decisioning is sequential and auditable. Each stage has a single responsibility and can be tested in isolation.

### 2.5 Hybrid ML + Rules Decisioning

Fraud outcomes (**ALLOW**, **REVIEW**, **BLOCK**) combine:

- **ML model** — calibrated LightGBM classifier loaded from `fraud_model.pkl`
- **Rule engine** — supplementary declarative checks
- **Threshold mapping** — score bands mapped to decisions

**Why:** ML captures complex patterns; rules provide interpretable guardrails. Hybrid approaches are common in production fraud systems where explainability and control matter.

### 2.6 Singleton Model Loading

The ML model and feature builder are loaded once per process via `@lru_cache` in `scoring_service.py`.

**Why:** Avoids reloading large artefacts on every request. Improves latency and memory predictability in production.

### 2.7 Schema / Model Separation

- **Pydantic schemas** (`src/schemas/`) — API input/output validation
- **SQLAlchemy models** (`src/db/models/`) — database persistence

**Why:** API contracts can evolve independently of the database schema. Prevents leaking ORM internals to HTTP responses.

### 2.8 RAG Pipeline (Retrieve → Generate → Validate → Cite)

The support assistant (`backend/rag/`) uses a Retrieval-Augmented Generation pipeline:

1. **Retrieve** — embed the question, search FAISS vector index
2. **Relevance gate** — refuse out-of-corpus questions below `MIN_RELEVANCE_SCORE`
3. **Generate** — Groq LLM with injected context
4. **Validate & cite** — check grounding markers and attach source references

**Why:** Grounds answers in project documentation, reduces hallucinations, and keeps the assistant secondary to the ML fraud engine.

### 2.9 Frontend Feature Modules

The Angular app (`frontend/src/app/`) is organized by feature:

- `features/` — landing, auth, overview, transactions, alerts, cases, watchlist
- `core/` — services, guards, models, stores
- `shared/` — reusable pipes and components
- `layout/` — shell and navigation

Routes use **lazy loading** and **route guards** (`authGuard`, `guestGuard`) in `app.routes.ts`.

**Why:** Features load on demand (smaller initial bundle). Guards enforce auth boundaries. Core services are injectable and testable in isolation.

### 2.10 Event Emitter

Side effects (e.g. alert creation after a flagged transaction) are decoupled via `event_emitter.py`.

**Why:** Keeps the main ingest path focused on scoring and persistence while allowing downstream reactions without tight coupling.

### 2.11 Infrastructure & Deployment Patterns

- **Containerized backend** — `backend/Dockerfile` ships ML artefacts and RAG index
- **Static frontend** — built and served from Render (`render.yaml`)
- **CI/CD** — GitHub Actions runs tests on every PR; backend auto-deploys to OCI on `main`
- **Secrets injection** — `DATABASE_URL`, `GROQ_API_KEY` via environment, never committed
- **Public rate limiting** — per-IP caps on unauthenticated routes (assistant, demo, access, health) via `slowapi`; returns HTTP `429` on abuse

**Why:** Reproducible builds, automated quality gates, and safe secret handling for production.

---

## 3. Testing Strategy

Testing is automated in CI (`.github/workflows/ci.yml`) and runnable locally. The approach combines **unit**, **integration**, and **smoke** testing across backend, ML, RAG, and frontend.

### 3.1 Backend — Unit Tests (pytest)

**Location:** `backend/tests/unit/`  
**Runner:** `pytest` with `pytest-cov`  
**CI command:** `python -m pytest -v --cov=ml --cov=src`

| Test file | What it covers | Method |
| --- | --- | --- |
| `test_decision_service.py` | Ingest pipeline, threshold mapping, serialization | Mocked DB sessions and scoring; async helpers |
| `test_scoring.py` | ML scoring service behaviour | Unit assertions on score outputs |
| `test_feature_builder.py` | Real-time feature construction | Isolated input/output checks |
| `test_feature_engineering.py` | ML feature engineering transforms | Deterministic fixture data |
| `test_preprocessing.py` | Data preprocessing steps | Edge-case inputs |
| `test_auth.py` | JWT verification logic | Token fixtures and mock JWKS |
| `test_alert_service.py` | Alert business rules | Service-level unit tests |
| `test_alert_crud_service.py` | Alert CRUD operations | Mocked persistence |
| `test_case_service.py` | Case lifecycle logic | Service-level unit tests |
| `test_watchlist_service.py` | Watchlist checks | Blacklist/whitelist scenarios |
| `test_watchlist_crud_service.py` | Watchlist CRUD | Mocked DB layer |

**Methods used:**
- `unittest.mock` / `pytest` fixtures for isolating services from the database
- In-memory `DATABASE_URL` in CI so imports succeed without a live Postgres instance
- Coverage reporting over `ml/` and `src/` packages

### 3.2 Backend — Integration Tests (pytest)

**Location:** `backend/tests/integration/`

| Test file | What it covers | Method |
| --- | --- | --- |
| `test_health.py` | `GET /health` endpoint | HTTP client against FastAPI app |
| `test_auth_routes.py` | Protected route auth behaviour | Request/response against live router |
| `test_ops_routes.py` | Operational API routes | End-to-end route tests with test client |

**Methods used:**
- FastAPI `TestClient` for HTTP-level verification
- Validates routing, status codes, and auth middleware integration

### 3.3 ML — Inference Tests

**Location:** `backend/ml/`

| Test file | What it covers | Method |
| --- | --- | --- |
| `test_inference.py` | Model inference on sample payloads | Loads artefact, asserts score shape/range |
| `test_inference_v2.py` | Updated model version inference | Same pattern for v2 calibrated model |

**Methods used:**
- Deterministic sample transactions
- Assertions on probability ranges and feature compatibility

### 3.4 RAG — Evaluation & Smoke Tests

**Offline evaluation:** `python -m rag.scripts.evaluate` (from `backend/`)

Measures on the production `RagSystem` pipeline:

| Metric | Purpose |
| --- | --- |
| Groundedness | In-corpus answers stay anchored to retrieved context |
| Citation accuracy | Answers cite the expected source document |
| Refusal accuracy | Out-of-corpus questions are refused without LLM call |
| Latency | Mean / p50 / p95 end-to-end response time |

Results are written to `rag/eval/results.json`.

**CI smoke test** (`.github/workflows/ci.yml` → `rag-index` job):

1. Build vector index from docs corpus
2. Assert in-corpus retrieval returns chunks above relevance floor
3. Assert out-of-corpus question is refused

**Why:** Retrieval and refusal logic are validated on every PR without requiring a Groq API key in CI.

### 3.5 Frontend — Unit Tests (Jest)

**Location:** `frontend/src/**/*.spec.ts`  
**Runner:** Jest with `jest-preset-angular`  
**CI command:** `npm test -- --ci --passWithNoTests`

| Area | Spec files | Method |
| --- | --- | --- |
| App bootstrap | `app.spec.ts` | Component creation smoke test |
| Auth guard | `auth.guard.spec.ts` | Route access with mocked auth state |
| Services | `alert.service.spec.ts`, `case.service.spec.ts`, `transaction.service.spec.ts`, `watchlist.service.spec.ts` | HTTP client mocking, observable assertions |
| Models | `transaction.model.spec.ts`, `watchlist.model.spec.ts` | Data mapping and type behaviour |
| Pipes | `decision-color.pipe.spec.ts`, `time-ago.pipe.spec.ts` | Transform input/output pairs |
| Components | `overview.component.spec.ts` | Component rendering with TestBed |

**Methods used:**
- Angular `TestBed` for component and guard setup
- Mocked `HttpClient` for service isolation
- Jest matchers for synchronous and async expectations

### 3.6 Continuous Integration Summary

| CI job | Trigger | Scope |
| --- | --- | --- |
| `backend-tests` | PR + push to `main` | pytest unit + integration, coverage on `ml` and `src` |
| `rag-index` | PR + push to `main` | Index build + retrieval/refusal smoke test |
| `frontend-tests` | PR + push to `main` | Jest unit tests across services, guards, pipes, components |

All jobs must pass before merge (branch protection on `main`).

---

## 4. Design Decisions Summary

| Decision | Rationale |
| --- | --- |
| ML as primary, RAG as support | Fraud decisions require calibrated, auditable scoring; the assistant is for guidance only |
| Service layer over fat controllers | Testable business logic, reusable across routes |
| Pydantic + SQLAlchemy split | Clean API contracts independent of DB schema |
| Lazy-loaded Angular features | Smaller bundles, faster initial load |
| Hybrid ML + rules | Balances predictive power with interpretability |
| RAG relevance gate | Prevents hallucinated answers on out-of-scope questions |
| CI smoke tests without API keys | Retrieval and refusal validated offline; generation tested locally with `GROQ_API_KEY` |
| Docker + GHCR + OCI deploy | Reproducible backend images with automated rollout |

---

## 5. Running Tests Locally

### Backend

```bash
cd backend
pip install -r requirements.txt pytest pytest-cov
DATABASE_URL="sqlite:///:memory:" python -m pytest -v --cov=ml --cov=src
```

### RAG evaluation

```bash
cd backend
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-rag.txt
python -m rag.scripts.build_vector_db
python -m rag.scripts.evaluate   # requires GROQ_API_KEY in .env
```

### Frontend

```bash
cd frontend
npm ci
npm test
```

---

**See also:** [README.md](README.md) · [deployed.md](deployed.md) · [ai-tooling.md](ai-tooling.md)
