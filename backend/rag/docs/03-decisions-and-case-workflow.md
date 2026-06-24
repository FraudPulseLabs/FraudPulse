# Decisions and Case Workflow

## The three decisions

Every scored transaction is classified into exactly one of three decisions:

- **ALLOW**: the transaction is cleared. The risk score is low and no
  overriding rule fired, so the payment proceeds without friction.
- **REVIEW**: the transaction is uncertain and needs a human analyst. It is
  held for investigation and generates an alert and a case.
- **BLOCK**: the transaction is high risk. It is declined and generates an
  alert and a case for follow-up.

## How decisions are determined

Decisions are produced by mapping the calibrated risk score to configurable
thresholds, combined with any rules that fired. A low score maps to ALLOW, a
middle band maps to REVIEW, and a high score maps to BLOCK. Rules can override
the score-based mapping to escalate a transaction.

Thresholds are configurable so that risk teams can tune the balance between
fraud capture and customer friction for their portfolio.

## Alerts

When a transaction results in REVIEW or BLOCK, FraudPulse creates an **alert**.
Alerts represent something that needs attention. Related alerts are grouped so
that analysts are not overwhelmed by duplicates from the same underlying
activity (for example repeated attempts on the same card).

## Cases

Alerts are organized into **cases**. A case is the unit of investigation an
analyst works. Cases have a lifecycle so that work can be tracked from
discovery to resolution. A typical lifecycle moves through states such as:

- **Open**: newly created and awaiting triage.
- **In progress**: an analyst is actively investigating.
- **Resolved**: a conclusion has been reached (for example confirmed fraud or
  legitimate).
- **Closed**: the case is complete and archived.

Every action taken on a case is recorded in the audit trail.

## Analyst workflow in the dashboard

Analysts use the FraudPulse dashboard to:

1. Monitor the live stream of scored transactions.
2. Triage incoming alerts as they are created.
3. Open and work cases, reviewing the score, the contributing features, and the
   rules that fired.
4. Add cards, devices, or accounts to watchlists when fraud is confirmed.
5. Resolve and close cases, leaving an auditable record of the outcome.

## Watchlists

Watchlists let analysts flag specific cards, devices, or accounts as known
risk. Watchlist membership influences future scoring and can cause rules to
fire, so confirmed fraud feeds back into the detection system. Watchlist
changes are versioned and recorded in history for auditability.
