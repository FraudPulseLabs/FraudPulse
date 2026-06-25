# FraudPulse Product Overview

## What is FraudPulse

FraudPulse is a real-time payment fraud detection platform for card and account
payments. It ingests transactions through a REST API, scores each one for fraud
risk using a calibrated machine-learning model and supporting rules, and routes
the outcome to a three-way decision. The goal is to stop fraudulent payments
before they settle while keeping friction low for legitimate customers.

FraudPulse is designed for payment processors, fintechs, marketplaces, and
banks that need sub-second risk decisions at the moment of authorization.

**Live deployments:**

- Frontend (dashboard and landing page): `https://fraudpulse-u2va.onrender.com/`
- Backend API documentation: `https://fraudpulse.duckdns.org/docs`
- Backend health check: `https://fraudpulse.duckdns.org/health`

## Who FraudPulse is for

FraudPulse serves two primary audiences:

- **Risk and fraud analysts**, who monitor transactions, triage alerts, and
  investigate cases in the Angular dashboard.
- **Engineering and product teams**, who integrate FraudPulse through the REST
  API to score transactions inline with checkout or authorization flows.

## Core capabilities

- **Real-time scoring**: every transaction receives a fraud risk score between
  0 and 1 during authorization, typically in milliseconds.
- **Hybrid detection**: a rule engine runs alongside a calibrated LightGBM
  model so known fraud patterns and emerging anomalies are both considered.
- **Three-way decisioning**: each transaction is classified into ALLOW, REVIEW,
  or BLOCK (dashboard labels). The API returns `APPROVE`, `APPROVE_WITH_REVIEW`,
  or `DECLINE` for the same outcomes.
- **Alerts and case management**: REVIEW and BLOCK outcomes create alerts that
  analysts group into cases for investigation.
- **Watchlists**: cards, devices, merchants, and accounts can be watchlisted to
  influence future scoring.
- **Explainability**: optional SHAP-style feature contributions explain why a
  transaction scored the way it did.
- **Audit trail**: decisions, score reasons, rule triggers, and case actions are
  logged for compliance and review.
- **AI support assistant**: a RAG-powered chatbot on the landing page answers
  product questions from this documentation. It is a support layer only — fraud
  decisioning is driven by the ML engine.

## Dashboard areas

Signed-in analysts use these main sections:

- **Overview** — high-level monitoring and metrics
- **Transactions** — scored transaction stream with ALLOW / REVIEW / BLOCK filters
- **Alerts** — queue of items needing attention
- **Cases** — investigation workflow from open to closed
- **Watchlist** — manage flagged entities

## How a transaction flows through FraudPulse

1. A transaction is submitted via `POST /api/v1/transactions` (or scored via the
   demo endpoints without persistence).
2. Watchlist and merchant-blacklist checks may short-circuit high-risk paths.
3. Real-time features are built from the payload and recent card history
   (amount patterns, velocity, temporal signals).
4. The rule engine evaluates deterministic policies in parallel with the model.
5. The calibrated LightGBM model produces a fraud probability score (0–1).
6. The score is mapped to APPROVE, APPROVE_WITH_REVIEW, or DECLINE using
   configurable thresholds.
7. `APPROVE_WITH_REVIEW` (REVIEW) and `DECLINE` (BLOCK) outcomes create alerts
   and cases for analysts.
8. The decision, score, reasons, and triggered rules are persisted and audited.
