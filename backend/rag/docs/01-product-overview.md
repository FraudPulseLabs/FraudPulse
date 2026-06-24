# FraudPulse Product Overview

## What is FraudPulse

FraudPulse is a real-time fraud detection platform for card and account
payments. It ingests payment transactions, scores each one for fraud risk
using a combination of deterministic rules and a calibrated machine-learning
model, and routes the outcome to one of three decisions: ALLOW, REVIEW, or
BLOCK. The goal is to stop fraudulent payments before they settle while
keeping friction low for legitimate customers.

FraudPulse is designed for payment processors, fintechs, marketplaces, and
banks that need sub-second risk decisions at the moment of authorization.

## Who FraudPulse is for

FraudPulse serves two primary audiences:

- **Risk and fraud analysts**, who monitor live transaction streams,
  investigate alerts, and work cases through the FraudPulse dashboard.
- **Engineering and product teams**, who integrate FraudPulse through its REST
  API to score transactions inline with their checkout or authorization flow.

## Core capabilities

- **Real-time scoring**: every transaction receives a fraud risk score in
  milliseconds during authorization.
- **Hybrid detection**: a rule engine runs alongside a calibrated LightGBM
  model so that both known fraud patterns and emerging anomalies are caught.
- **Three-way decisioning**: each transaction is classified as ALLOW, REVIEW,
  or BLOCK based on configurable thresholds.
- **Alerts and case management**: flagged transactions generate alerts that are
  grouped into cases for analyst investigation.
- **Watchlists**: cards, devices, and accounts can be added to watchlists that
  influence future scoring.
- **Audit trail**: every decision, score reason, and case action is logged for
  compliance and review.

## Key benefits

- Reduce fraud losses by blocking high-risk payments before settlement.
- Lower manual review volume by auto-approving clearly legitimate traffic.
- Give analysts a single workspace for alerts, cases, and watchlists.
- Maintain explainability: each score is accompanied by the top contributing
  features and any rules that fired.

## How a transaction flows through FraudPulse

1. A transaction is submitted to FraudPulse through the REST API.
2. Real-time features are extracted, including amount patterns and velocity
   (activity over rolling time windows).
3. The rule engine evaluates the transaction against configured rules.
4. The calibrated LightGBM model produces a fraud risk score.
5. The combined result is mapped to an ALLOW, REVIEW, or BLOCK decision.
6. REVIEW and BLOCK outcomes create alerts and cases for analysts.
7. The decision, score, reasons, and any triggered rules are persisted to the
   audit trail.
