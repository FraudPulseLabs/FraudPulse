# Security and Compliance

## Authentication and access control

FraudPulse protects application APIs with **Supabase JWT authentication**.
Protected routes under `/api/v1` require:

```
Authorization: Bearer <supabase-jwt>
```

**Public endpoints** (no JWT required):

- `GET /health`
- `GET /api/v1/demo/transactions`
- `POST /api/v1/demo/score`
- `POST /api/v1/access/requests`
- `POST /api/v1/assistant/chat`

Public routes are **rate-limited per client IP** to reduce abuse (assistant LLM
cost, demo scoring load, and access-request spam). Excess traffic receives HTTP
`429 Too Many Requests`.

Tokens are minted by Supabase Auth on the frontend and verified by the backend
against the project's public JWKS. The FraudPulse backend does not handle raw
passwords or issue its own credentials.

## Data protection in transit

All traffic between the browser, API, and database uses **TLS encryption**.
Database connections to Supabase Postgres require SSL (`sslmode=require` in the
connection string).

## Secrets management

Sensitive configuration is provided through **environment variables** and
never committed to git:

| Secret | Purpose |
| --- | --- |
| `DATABASE_URL` | Supabase/Postgres connection |
| `GROQ_API_KEY` | RAG assistant LLM generation |

Local development uses a gitignored `backend/.env` file. Production injects
secrets through Render, OCI deployment, or GitHub Actions secrets.

## Audit trail

FraudPulse records scores, score reasons, triggered rules, decisions, case
actions, and watchlist changes. Watchlist updates are **versioned with history**
so every change is traceable. This supports investigation, accountability, and
regulatory review.

## Explainability for compliance

The calibrated model stores **top contributing features** per score (available
with `explain=true` on ingest/score). Combined with rule triggers, FraudPulse
can explain why a transaction was allowed, sent to review, or blocked — supporting
adverse-action and fair-lending style requirements.

## Privacy and data isolation for the assistant

The landing-page **RAG assistant**:

- Answers only from FraudPulse product documentation
- Does **not** access customer transaction data or the production database
- Does **not** store visitor conversations in the documentation corpus
- Refuses out-of-scope questions rather than guessing

This keeps the public assistant isolated from sensitive operational data.

## Responsible AI

The assistant is constrained by design:

1. Retrieval from a curated corpus before any LLM call
2. Relevance threshold — low-similarity questions are refused
3. System prompt forbids inventing features, endpoints, or guarantees
4. Citations required for grounded answers

Fraud **decisioning** is not performed by the LLM — it is performed by the
calibrated ML model and rule engine.
