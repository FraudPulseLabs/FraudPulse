# Frequently Asked Questions

## What does FraudPulse do?

FraudPulse is a real-time fraud detection platform for card and account
payments. It scores each transaction for fraud risk (0–1) and routes it to
**ALLOW**, **REVIEW**, or **BLOCK** — helping stop fraud before settlement while
keeping friction low for legitimate customers.

## What are the allow, review, and block decisions?

Three outcomes exist for every transaction:

| Label (dashboard) | API value | Meaning |
| --- | --- | --- |
| ALLOW | `APPROVE` | Cleared — low risk |
| REVIEW | `APPROVE_WITH_REVIEW` | Held for analyst investigation |
| BLOCK | `DECLINE` | Declined — high risk |

REVIEW and BLOCK create alerts and cases.

## How fast is transaction scoring?

Scoring runs in **real time**, typically within **milliseconds**, so it fits
inline during payment authorization without noticeable latency.

## Does FraudPulse use machine learning or rules?

**Both.** A deterministic rule engine runs alongside a **calibrated LightGBM**
model. Rules capture known patterns; the model catches subtler anomalies. The
ML engine is the primary decision layer.

## What machine learning model does FraudPulse use?

A **calibrated LightGBM** gradient-boosted tree model. It outputs a fraud
probability between 0 and 1. Thresholds map scores to APPROVE,
APPROVE_WITH_REVIEW, or DECLINE.

## How does FraudPulse extract features for scoring?

A real-time feature builder creates vectors from the transaction payload and
card history — including **amount**, **velocity** (recent transaction counts),
temporal signals, and entity/watchlist features. Feature order is defined in
the model schema (`GET /api/v1/scoring/schema`).

## Can I see why a transaction was flagged?

Yes. Scores store top contributing features and any rules that fired. Use
`?explain=true` on ingest or score endpoints for SHAP-style contributions.
Analysts also see explanations in the dashboard audit trail.

## What is the difference between an alert and a case?

An **alert** is a single item needing attention (created on REVIEW or BLOCK).
A **case** is the investigation unit — related alerts are grouped into a case
with a lifecycle from open to closed.

## How do I integrate FraudPulse?

Send transactions to `POST /api/v1/transactions` under `/api/v1`. Protected
endpoints need a Supabase JWT in the `Authorization` header. See the API
Reference for full endpoint details.

## Is there a way to try FraudPulse without signing up?

Yes. The **model demo** on the landing page and `POST /api/v1/demo/score` let
you score sample transactions without an account or database writes.

## How is FraudPulse hosted?

- **Frontend:** Angular on Render (`fraudpulse-u2va.onrender.com`)
- **Backend:** FastAPI in Docker on Oracle Cloud (`fraudpulse.duckdns.org`)
- **Database:** Postgres via Supabase

## What is the tech stack behind FraudPulse?

**FastAPI** (Python) backend, **Angular 21** frontend with **Tailwind CSS**,
**Supabase Postgres**, **LightGBM** for ML, and a **RAG** pipeline (FAISS +
Groq LLM) for the landing-page assistant.

## How does authentication work in the API?

Protected routes require a **Supabase-issued JWT** bearer token. The backend
verifies tokens via JWKS. Public routes include health, demo, access requests,
and the assistant.

## Is FraudPulse data encrypted in transit?

Yes. All client-to-API and API-to-database traffic uses **TLS**. Database
connections require SSL (`sslmode=require`).

## How do I get access to FraudPulse?

Use the **Request access** form on the landing page with your work email. The
team follows up within about one business day.

## How much does FraudPulse cost?

Pricing is not listed publicly and depends on volume and use case. Submit the
Request access form for details.

## How do I contact the team?

Use the **Request access** form on `https://fraudpulse-u2va.onrender.com/`.
The team responds within one business day.

## What powers the landing-page assistant?

A **retrieval-augmented generation (RAG)** pipeline: embed the question, search
a FAISS index of FraudPulse documentation, inject context into a **Groq LLM**,
and return a cited answer. Out-of-scope questions are refused. The assistant
does not score transactions or access customer data.

## Does the assistant replace the fraud model?

No. The assistant is a **support layer** for documentation questions only.
Fraud decisions are made by the **ML model and rule engine**.
