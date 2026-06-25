# Decisions and Case Workflow

## ALLOW, REVIEW, and BLOCK decisions

Every scored transaction receives exactly one decision. FraudPulse uses two
naming conventions for the same three outcomes:

| Dashboard / product label | API value | Meaning |
| --- | --- | --- |
| **ALLOW** | `APPROVE` | Low risk; payment proceeds without friction |
| **REVIEW** | `APPROVE_WITH_REVIEW` | Uncertain; held for analyst investigation |
| **BLOCK** | `DECLINE` | High risk; payment declined |

When users ask about **allow, review, or block** decisions, these map directly
to the API values above.

## How decisions are determined

Decisions are produced by mapping the calibrated fraud score (0–1) to
thresholds, combined with any rules that fired:

1. If the score is **below** `approve_below` → `APPROVE` (ALLOW).
2. If the score is **at or above** `decline_from` → `DECLINE` (BLOCK).
3. Otherwise → `APPROVE_WITH_REVIEW` (REVIEW).

Rules can override score-based mapping to force escalation. Thresholds are
tunable per portfolio.

## Which outcomes create alerts

`APPROVE_WITH_REVIEW` (REVIEW) and `DECLINE` (BLOCK) outcomes generate
**alerts** for analyst attention. `APPROVE` (ALLOW) does not.

Common alert reasons include fraud-review-required and fraud-score-decline
signals tied to the decision type.

## Alerts

An **alert** is a single item needing attention, created when a transaction
lands in REVIEW or BLOCK. Related alerts may be grouped so analysts are not
overwhelmed by duplicate activity on the same card or account.

## Cases

Alerts feed into **cases** — the unit of investigation. Cases have a lifecycle:

- **Open** — newly created, awaiting triage
- **In progress** — actively under investigation
- **Resolved** — conclusion reached (confirmed fraud or legitimate)
- **Closed** — complete and archived

Every case action is recorded in the audit trail.

## Analyst workflow in the dashboard

Analysts typically:

1. Monitor the transaction stream on the **Transactions** page.
2. Triage new **Alerts** as they arrive.
3. Open **Cases**, review the score, contributing features, and triggered rules.
4. Add confirmed fraud entities to the **Watchlist**.
5. Resolve and close cases with an auditable outcome.

## Watchlists

Watchlists flag specific cards, devices, merchants, or accounts as known risk.
Membership influences future scoring and can cause rules to fire, so confirmed
fraud feeds back into detection. Changes are versioned in watchlist history for
auditability.

## Transaction ingest vs read-only queries

- `POST /api/v1/transactions` — full ingest pipeline (score, decide, persist,
  optionally create alerts/cases). Supports `?explain=true` for feature
  contributions.
- `GET /api/v1/transactions` — list recent transactions.
- `GET /api/v1/transactions/{id}` — single transaction with latest score and reasons.
