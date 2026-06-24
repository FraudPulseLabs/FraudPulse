# Security and Compliance

## Authentication and access control

FraudPulse protects its application API with authentication. Every endpoint
under ``/api/v1`` requires a valid Supabase-issued JWT, except a small set of
public endpoints (the model demo, access requests, and the landing-page
assistant). Tokens are issued by Supabase Auth and verified by the backend
against the project's public JWKS, so credentials are never handled directly by
the FraudPulse backend.

## Data protection in transit

All traffic between the dashboard, the API, and the database is encrypted in
transit using TLS. Database connections to Supabase Postgres require SSL
(``sslmode=require``).

## Secrets management

Secrets — including the database connection string and the Groq API key used by
the assistant — are provided through environment variables and never committed
to source control. Local development uses a gitignored ``.env`` file, and
production injects secrets through the deployment environment.

## Audit trail

FraudPulse maintains a comprehensive audit trail. Scores, score reasons,
triggered rules, decisions, case actions, and watchlist changes are all
recorded. This supports investigation, accountability, and regulatory review.
Watchlist changes in particular are versioned with history so any change can be
traced to who made it and when.

## Explainability for compliance

Because the model is calibrated and each prediction stores its top contributing
features alongside any rules that fired, FraudPulse can explain why any given
transaction was allowed, sent to review, or blocked. Explainability supports
fair-lending and adverse-action style requirements where a reason for a
decision must be available.

## Privacy considerations

The landing-page assistant answers only from FraudPulse's own product
documentation. It does not have access to customer transaction data, personal
data, or the production database, and it does not store user conversations as
part of the corpus. This keeps the public assistant isolated from sensitive
data.

## Responsible AI

The assistant is constrained by design: it answers strictly from the curated
documentation corpus and refuses questions it cannot ground in that corpus,
rather than guessing. This reduces the risk of hallucinated or misleading
statements about the product.
