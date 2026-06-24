# Scoring Methodology

## Overview of scoring

FraudPulse scores every transaction in real time. Scoring combines a
deterministic rule engine with a calibrated machine-learning model. The rule
engine captures known, explainable fraud patterns, while the model detects
subtler and emerging anomalies. The two run together and their results are
combined to produce the final risk score and decision.

## Feature extraction

Before scoring, FraudPulse builds a feature vector for the transaction from the
incoming payload and recent history for the card or account. Engineered
features include:

- **Amount features**: the transaction amount, and how it compares to the
  card's historical mean and standard deviation of spend.
- **Velocity features**: counts of recent transactions over rolling time
  windows (for example the last hour and last 24 hours), which capture bursts
  of activity that often indicate card testing or takeover.
- **Temporal features**: time-of-day and recency signals derived from the
  transaction timestamp and the time since the previous transaction.
- **Entity features**: signals associated with the card, device, and account,
  including whether any of them appear on a watchlist.

Feature extraction is performed by a real-time feature builder so that scoring
reflects the most current behaviour at the moment of authorization.

## The machine-learning model

FraudPulse uses a gradient-boosted decision tree model trained with LightGBM.
The model is **calibrated** so that its output behaves like a true probability
of fraud, which makes thresholds meaningful and stable across time.

Key properties of the model:

- It outputs a fraud risk score between 0 and 1, where higher means riskier.
- It is calibrated (for example with isotonic or Platt scaling) so scores can
  be compared to fixed decision thresholds.
- It is explainable: for any prediction FraudPulse can surface the top
  contributing features so analysts understand why a transaction scored the way
  it did.

## The rule engine

The rule engine evaluates each transaction against a set of deterministic
rules in parallel with the model. Rules encode policies and known fraud
patterns — for example flagging transactions tied to watchlisted entities or
matching a high-risk pattern. When a rule fires, it is recorded as a rule
trigger and contributes to the final decision and the audit trail.

## Combining rules and the model

The final decision is driven by the combination of the calibrated model score
and any rules that fired. Rules can escalate a decision (for example forcing a
REVIEW or BLOCK) regardless of the model score, while the model score drives
the decision in the absence of overriding rules.

## Explainability and score reasons

Every score is stored with score reasons: the top contributing model features
and the list of rules that triggered. This explainability is available to
analysts in the dashboard and is recorded in the audit trail, supporting both
investigation and compliance.
