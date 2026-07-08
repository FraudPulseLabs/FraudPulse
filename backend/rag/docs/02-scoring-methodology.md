# Scoring Methodology

## Overview of fraud scoring

FraudPulse scores every transaction in real time. Scoring combines a
deterministic rule engine with a calibrated machine-learning model. The rule
engine captures known, explainable fraud patterns; the model detects subtler and
emerging anomalies. Both run together to produce a fraud risk score between
**0 and 1**, where higher values mean higher fraud risk.

Scoring is the **primary intelligence layer** in FraudPulse. The landing-page
assistant does not perform scoring — it only answers documentation questions.

## Feature extraction

Before scoring, FraudPulse builds a feature vector from the incoming transaction
and recent history for the card or account. The real-time feature builder
engineers signals such as:

- **Amount features** — transaction amount and deviation from the card's
  historical mean and standard deviation.
- **Velocity features** — counts of recent transactions over rolling windows
  (for example the last hour and last 24 hours), capturing bursts of activity
  common in card testing or account takeover.
- **Temporal features** — time-of-day and recency derived from timestamps.
- **Entity features** — card, device, merchant, and account signals, including
  watchlist membership and merchant-category fraud rates.

Feature order and decision thresholds are defined in the model artefact schema
(`feature_schema.json`) and exposed via `GET /api/v1/scoring/schema`.

## The machine-learning model

FraudPulse uses a **gradient-boosted decision tree model trained with LightGBM**.
The model is **calibrated** (for example with isotonic or Platt scaling) so its
output behaves like a true fraud probability.

Key properties:

- Outputs a score between **0 and 1** (higher = riskier).
- Calibrated probabilities make threshold bands meaningful over time.
- Explainable: with `explain=true`, the API returns top contributing features
  (SHAP-style contributions) so analysts understand why a transaction scored as
  it did.

## The rule engine

The rule engine evaluates each transaction against deterministic rules in
parallel with the model. Rules encode policies and known patterns — for example
watchlisted entities or high-risk merchant behaviour. When a rule fires, it is
recorded as a **rule trigger** in the audit trail and may escalate the final
decision.

## Combining rules and the model

The final decision maps the calibrated score to thresholds, then applies any
rule overrides:

| Score band (default policy) | API decision | Dashboard label |
| --- | --- | --- |
| Below approve threshold | `APPROVE` | ALLOW |
| Between approve and decline thresholds | `APPROVE_WITH_REVIEW` | REVIEW |
| At or above decline threshold | `DECLINE` | BLOCK |

Default thresholds (from the shipped model schema) are approximately:

- **approve_below**: 0.011 — scores below this are APPROVE (ALLOW)
- **decline_from**: 0.995 — scores at or above this are DECLINE (BLOCK)
- Scores between those values are APPROVE_WITH_REVIEW (REVIEW)

Thresholds are configurable per deployment so risk teams can tune the balance
between fraud capture and customer friction.

## Merchant blacklist short-circuit

Before full scoring, transactions tied to blacklisted merchants may be
short-circuited to a high-risk outcome without running the full ML pipeline.

## Explainability and score reasons

Every persisted score stores **score reasons**: top contributing model features
and any rules that triggered. Analysts see this in the dashboard; it is also
recorded in the audit trail for investigation and compliance.
