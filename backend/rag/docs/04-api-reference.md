# API Reference

## API overview

FraudPulse exposes a **REST API** with JSON request and response bodies. Versioned
application endpoints live under the `/api/v1` prefix.

- **Interactive docs (Swagger UI):** `/docs` — e.g. `https://fraudpulse.duckdns.org/docs`
- **Health check:** `GET /health` — no authentication required
- **Base path for app routes:** `/api/v1`

Most endpoints require a Supabase-issued JWT. A small set of public endpoints
supports the landing page, access requests, model demo, and documentation
assistant.

## Authentication

Protected endpoints require a bearer token:

```
Authorization: Bearer <supabase-jwt>
```

FraudPulse does **not** issue tokens. The Angular frontend obtains tokens from
**Supabase Auth**; the backend verifies them via the project's public JWKS.
Invalid or missing tokens on protected routes return `401 Unauthorized`.

## Health check

- `GET /health` — returns service status and a UTC timestamp. Used by load
  balancers, deployment workflows, and uptime monitoring. No auth required.

## Core endpoint groups (authenticated)

All groups below require a valid JWT unless noted.

| Prefix | Purpose |
| --- | --- |
| `/api/v1/transactions` | Ingest transactions and query history |
| `/api/v1/scoring` | Score without full ingest; feature schema |
| `/api/v1/decisions` | Decision workflow endpoints |
| `/api/v1/alerts` | List and manage fraud alerts |
| `/api/v1/cases` | Case lifecycle (open, update, resolve, close) |
| `/api/v1/watchlist` | Watchlisted cards, devices, merchants, accounts |
| `/api/v1/profiles` | Entity profiles and history |
| `/api/v1/admin` | Administrative operations |
| `/api/v1/auth` | Authenticated user helpers |

## Key transaction endpoints

### Ingest a transaction (full pipeline)

```
POST /api/v1/transactions?explain=false
```

Runs watchlist checks, feature building, ML scoring, threshold mapping,
persistence, and optional alert/case creation. Set `explain=true` to include
top contributing features in the response.

### List and retrieve transactions

```
GET /api/v1/transactions
GET /api/v1/transactions/{transaction_id}
```

## Scoring endpoints

```
POST /api/v1/scoring/score?explain=false
GET  /api/v1/scoring/schema
```

`/score` runs the model without the full ingest persistence path. `/schema`
returns feature order and decision thresholds from the loaded model artefact.

## Public endpoints (no JWT)

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service health |
| `POST /api/v1/demo/transactions` | Fixture demo transactions |
| `POST /api/v1/demo/score` | Score a demo transaction without DB writes |
| `POST /api/v1/access/requests` | Submit early-access request from landing page |
| `POST /api/v1/assistant/chat` | Landing-page RAG assistant (documentation Q&A) |

### Assistant chat

```
POST /api/v1/assistant/chat
Body: { "question": "How does scoring work?" }
```

Returns a grounded answer with source citations from the FraudPulse
documentation corpus. Out-of-scope questions are refused without guessing.

## HTTP status codes and errors

| Code | Meaning |
| --- | --- |
| `400` | Malformed request or validation error |
| `401` | Missing or invalid authentication |
| `404` | Resource not found |
| `5xx` | Server error |

Error bodies include a `detail` field describing the problem.
