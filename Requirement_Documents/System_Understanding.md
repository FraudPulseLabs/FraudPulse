# FraudPulse — Team Scope & System Understanding

## 1. System Purpose

### What We Are Building

We are building a **real-time fraud risk scoring system** that sits between a transaction processor (Payments switch) and a Card Management System (CMS).

The system evaluates incoming transactions for potential fraud and returns a fraud decision indicator that the CMS can use during authorization.

The project simulates how modern fraud detection systems work in banking environments while remaining technically achievable within the project timeline.

## 2. What Business Problem This Solves

Banks process thousands of transactions every second.

Blocking every suspicious transaction creates:

- poor customer experience
- false declines
- lost revenue

Allowing everything creates:

- financial loss
- fraud exposure

This system helps balance:

- fraud prevention
- customer experience
- operational monitoring

The system provides:

- real-time fraud scoring
- configurable fraud decisions
- merchant watchlist enforcement
- fraud investigation workflows
- operational dashboards

## 3. Important Scope Clarification

### This System Is NOT

We are **not** building:

- a card authorization system
- a core banking platform
- ISO 8583 routing
- settlement processing
- customer account management

The Card Management System still handles:

- card status
- spending limits
- authorization rules
- hard transaction velocity controls

The core banking system still handles:

- balances

## 4. What Our System DOES

Our system:

1. Receives transaction data
2. Evaluates fraud risk
3. Returns a fraud decision
4. Stores fraud analysis data
5. Creates investigation cases
6. Provides fraud monitoring dashboards

## 5. Core Business Logic

### Possible Decisions

| Decision              | Meaning                                                    |
| --------------------- | ---------------------------------------------------------- |
| **ALLOW**             | Transaction appears legitimate                             |
| **ALLOW_WITH_REVIEW** | Transaction approved but flagged for analyst investigation |
| **BLOCK**             | Transaction considered high fraud risk                     |

## 6. Important Understanding of ALLOW_WITH_REVIEW

This is extremely important.

**ALLOW_WITH_REVIEW DOES NOT:**

- delay the transaction
- pause authorization
- require customer confirmation

**ALLOW_WITH_REVIEW DOES:**

- approve the transaction
- create an internal fraud alert
- notify analysts for investigation

**Example:** Customer purchase succeeds. Fraud team later investigates suspicious behavior. This mirrors how real banks often operate.

## 7. Real-Time Transaction Flow (Detailed)

### Step 1 — Transaction Received

**Purpose:** Receive transaction data from upstream system.

**Example Request**

```json
{
  "transaction_id": "TX1001",
  "customer_id": "CUST900",
  "merchant_id": "M100",
  "amount": 250.0,
  "currency": "USD",
  "timestamp": "2026-05-10T10:30:00Z"
}
```

**Operations**

- Validate schema
- Validate required fields
- Generate internal request ID
- Log request

### Step 2 — Merchant Watchlist Check

**Purpose:** Immediately block known high-risk merchants.

**Why This Happens First**

ML scoring is unnecessary if:

- merchant already known fraudulent
- merchant manually blacklisted
- merchant auto-blacklisted

This improves:

- performance
- efficiency
- explainability

**Operations** — system checks:

- blacklist table
- blacklist expiry dates
- blacklist status

**Possible Outcomes**

- **Merchant Blacklisted:** Decision = `BLOCK`, Reason = `MERCHANT_BLACKLISTED`. ML scoring is skipped.
- **Merchant Not Blacklisted:** Continue to scoring pipeline.

### Step 3 — Feature Engineering

**Purpose:** Transform raw transaction data into ML features.

**Important Clarification** — we are **not** implementing:

- CMS velocity rules
- card authorization logic

We only calculate features useful for fraud scoring.

**Example Features**

| Feature                    | Description              |
| -------------------------- | ------------------------ |
| `merchant_fraud_rate`      | Historical fraud rate    |
| `recent_customer_activity` | Customer activity window |
| `transaction_hour`         | Time-of-day              |
| `cross_border_flag`        | Country mismatch         |
| `merchant_risk_level`      | Merchant risk category   |

**Operations** — system:

- Retrieves supporting historical data
- Computes derived features
- Prepares ML input vector

### Step 4 — Fraud Scoring Engine

**Purpose:** Generate fraud probability using trained ML model.

**Operations** — model:

- Loads serialized model
- Receives feature vector
- Predicts fraud probability

**Example Output**

```json
{ "fraud_score": 0.87 }
```

### Step 5 — Decision Engine

**Purpose:** Convert fraud score into operational decision.

**Decision Logic** — example thresholds (configurable):

| Score Range | Decision            |
| ----------- | ------------------- |
| 0.00–0.39   | `ALLOW`             |
| 0.40–0.74   | `ALLOW_WITH_REVIEW` |
| 0.75–1.00   | `BLOCK`             |

**Additional Rules** — rules may override the ML score, e.g.:

- merchant blacklisted
- extremely abnormal behavior
- analyst-defined overrides

**Example Final Response**

```json
{
  "transaction_id": "TX1001",
  "decision": "ALLOW_WITH_REVIEW",
  "fraud_score": 0.63,
  "reason_code": "HIGH_RISK_PATTERN"
}
```

### Step 6 — Return Response to CMS

**Purpose:** Provide fraud indicator to upstream authorization system.

**Important:** the CMS decides:

- whether to approve the card transaction
- whether to decline the transaction
- whether additional controls apply

Our system only provides:

- fraud assessment
- recommendation indicator

## 8. Asynchronous Processing (After Response)

This happens **after** the API response returns. Critical for performance.

**Why Async Exists:** heavy operations should not delay `POST /transaction`.

**Async Operations (pipeline)**

```
Transaction Completed
      │
      ▼
Generate Alert
      │
      ▼
Update Case
      │
      ▼
Update Merchant Metrics
      │
      ▼
Generate Explanation
      │
      ▼
Update Dashboard Data
```

## 9. Alert Management

**Purpose:** Track suspicious transactions requiring attention.

**When Alerts Are Created** — create an alert when:

- decision = `ALLOW_WITH_REVIEW`
- decision = `BLOCK`

**Alert Example**

| Field            | Value             |
| ---------------- | ----------------- |
| `alert_id`       | ALT1001           |
| `transaction_id` | TX1001            |
| `severity`       | HIGH              |
| `reason`         | HIGH_RISK_PATTERN |
| `status`         | OPEN              |

## 10. Case Management

**Purpose:** Fraud analysts investigate groups of suspicious activity instead of isolated transactions.

**Why Cases Matter**

Without cases:

- analysts ALLOW_WITH_REVIEW transactions individually
- patterns are missed
- duplicated investigations occur

With cases:

- related fraud activity grouped together
- investigations organized
- workflow manageable

**Example Case**

```
Case ID: CASE-3001
Customer: CUST900
Transactions:
  - TX1001
  - TX1007
  - TX1012
Reasons:
  - unusual spending pattern
  - repeated fraud indicators
Status: INVESTIGATING
```

**Case Lifecycle**

```
OPEN → INVESTIGATING → RESOLVED / FALSE_POSITIVE
```

**Case Creation Logic** — simple MVP logic:

- multiple suspicious transactions
- repeated merchant flags
- repeated customer ALLOW_WITH_REVIEW decisions

## 11. Merchant Monitoring

**Purpose:** Track merchant fraud trends over time.

**Important:** this is analytical monitoring / operational intelligence. This is **not** settlement management or merchant account control.

**Example Merchant Metrics**

| Metric                   | Meaning                               |
| ------------------------ | ------------------------------------- |
| `ALLOW_WITH_REVIEW_rate` | % of transactions ALLOW_WITH_REVIEWed |
| `decline_rate`           | % blocked                             |
| `fraud_score_avg`        | Average fraud score                   |
| `suspicious_txn_count`   | Suspicious transaction volume         |

## 12. Fraud Metrics & Analytics

**Purpose:** Provide operational visibility into system behavior.

**Example Metrics**

| Metric                   | Purpose                        |
| ------------------------ | ------------------------------ |
| `total_transactions`     | System volume                  |
| `fraud_rate`             | Suspected fraud percentage     |
| `approval_rate`          | Operational behavior           |
| `ALLOW_WITH_REVIEW_rate` | Analyst workload               |
| `decline_rate`           | Fraud prevention effectiveness |

## 13. Explainability

**Goal:** Allow analysts to understand _why_ a transaction was flagged.

**Important Performance Rule:** explanation generation must **not** happen inside the real-time API path.

**Real-Time API Returns Only**

```json
{ "decision": "BLOCK", "reason_code": "HIGH_RISK_PATTERN" }
```

**Explanation Generated Asynchronously** — examples:

- unusual customer behavior
- high merchant fraud rate
- abnormal timing pattern
- elevated model risk contribution

## 14. Merchant Watchlist System

**Purpose:** Allow manual and automatic merchant blocking.

**CRUD Operations** — operators can:

- add merchant
- remove merchant
- update expiry date
- search merchant
- view blacklist history

**Auto-Blacklist Rule Example**

```
IF merchant exceeds fraud threshold
THEN add merchant to blacklist
```

## 15. UI Components

**Transaction Dashboard** — displays: transactions, fraud scores, decisions, timestamps, filters, search.

**Case Dashboard** — displays: open cases, linked transactions, statuses, analyst workflow.

**Merchant Watchlist UI** — displays: blocked merchants, expiry dates, blacklist reasons, merchant statistics.

## 16. Suggested Team Ownership

**Backend Team**

- Flask
- Scoring engine
- Decision engine
- Database
- Async processing

**ML Team**

- Preprocessing
- Feature engineering
- Model training
- Threshold tuning
- Explainability

**Frontend Team**

- Dashboards
- Filters / search
- Case UI
- Watchlist UI

## 17. Most Important Architectural Rule

Only these happen synchronously:

```
validate → watchlist check → feature engineering → fraud scoring → decision → response
```

Everything else must be asynchronous.
