# API Reference

## API overview

FraudPulse exposes a REST API. All application endpoints are served under the
``/api/v1`` prefix. Responses are JSON. Most endpoints require authentication
with a Supabase-issued JWT; a small number of public endpoints exist for the
landing page and the model demo.

The interactive API documentation is available at ``/docs`` (Swagger UI) when
the service is running.

## Authentication

Protected endpoints require a bearer token in the ``Authorization`` header:

```
Authorization: Bearer <supabase-jwt>
```

FraudPulse does not issue tokens itself. Tokens are minted by Supabase Auth on
the frontend, and the backend verifies them using the project's public JWKS.
Requests without a valid token to a protected route receive ``401
Unauthorized``.

## Health check

- ``GET /health`` — returns service status and a timestamp. No authentication
  required. Useful for uptime monitoring and load-balancer health probes.

## Core endpoint groups

The API is organized into the following groups, all under ``/api/v1``:

- ``/transactions`` — ingest and query transactions.
- ``/scoring`` — score transactions and retrieve scores.
- ``/decisions`` — retrieve decision outcomes (ALLOW / REVIEW / BLOCK).
- ``/alerts`` — list and manage alerts.
- ``/cases`` — work the case lifecycle (open, update, resolve, close).
- ``/watchlist`` — manage watchlisted cards, devices, and accounts.
- ``/profiles`` — entity profiles and history.
- ``/admin`` — administrative operations.
- ``/auth`` — authenticated user/account helpers.

These groups require a valid JWT.

## Public endpoints

A few endpoints are intentionally public so the marketing site and demo work
without sign-in:

- ``/api/v1/demo/transactions`` — returns a fixture set of demo transactions.
- ``/api/v1/demo/score`` — scores a demo transaction through the model without
  persisting to the database, so prospective users can try scoring.
- ``/api/v1/access/requests`` — submit a request for early access to the
  dashboard and API.
- ``/api/v1/assistant/chat`` — the public landing-page assistant, which answers
  product questions from the FraudPulse documentation.

## Scoring a transaction

To score a transaction, submit its details to the scoring endpoint. The
response includes the fraud risk score, the resulting decision, the model name,
and (when explanations are requested) the top contributing features. Scoring
the demo endpoint uses cold-start card history and does not write to the
database.

## Rate limits and errors

The API uses standard HTTP status codes. ``400`` indicates a malformed request,
``401`` an authentication failure, ``404`` a missing resource, and ``5xx`` a
server error. Error responses include a ``detail`` field describing the problem.
