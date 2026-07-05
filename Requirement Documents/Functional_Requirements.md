# FraudPulse — Functional Requirements

*Canonical numbering FR-1 to FR-19, aligned with the Backlog v1.1 traceability matrix and epics E1–E14. See `CHANGELOG.md` for how this numbering was reconciled from earlier drafts.*

| Field | Value |
|---|---|
| Document title | FraudPulse Functional Requirements |
| Version | 1.2 (harmonized) |
| Status | Draft for team curation |
| Owner | Capstone team |

## FR-1. User Authentication and Roles

1.1 Secure user login
1.2 User roles — Customer, System Administrator, Fraud Analyst, Support/Dispute Handler, FraudPulse System
1.3 Restrict access based on user role (least privilege)
1.4 User and activity logs
1.5 System Administrator can manage users and assign roles

## FR-2. Transaction Ingestion

2.1 Exposes a REST API endpoint for transaction submission
2.2 The system shall accept and record transaction ID, user ID, amount, timestamp, merchant, user public IP, and location/device data
2.3 Validate incoming transaction data
2.4 Reject invalid or incomplete transaction requests
2.5 Store all submitted transactions — valid, invalid, allowed, or blocked
2.6 Support manual transaction entry from the UI
2.7 Prevent duplicate transaction IDs

## FR-3. Fraud Scoring

3.1 Preprocess transaction data before scoring
3.2 Compute a fraud probability score for each transaction
3.3 Return the fraud score through the API
3.4 Store the fraud score for each transaction
3.5 Allow fraud scoring to be re-run on selected transactions
3.6 Log scoring time and model output
3.7 Provide an explanation for fraud scores where possible
3.8 Load a trained fraud detection model

## FR-4. Real-Time Decision Engine

4.1 Classify transactions as `ALLOW`, `REVIEW`, or `BLOCK`
4.2 Allow low-risk transactions to proceed
4.3 Block high-risk transactions
4.4 Configurable fraud score thresholds
4.5 Place medium-risk transactions into review
4.6 Store the final transaction decision
4.7 Allow threshold configuration by an admin

## FR-5. Rule-Based Fraud Detection

5.1 Detect unusually high transaction amounts
5.2 Detect repeated transactions within a short time
5.3 Detect unusual merchant and user activity
5.4 Detect transactions from risky merchants

## FR-6. Watchlist Management

6.1 Add high-risk transactions to a blacklist
6.2 Add medium-risk transactions to a watchlist with reasons
6.3 Allow analysts to view watch-listed transactions
6.4 Allow analysts to remove transactions from the watchlist
6.5 Allow users/merchants to be placed on a watchlist
6.6 Maintain a history of watchlist changes

## FR-7. Alert Generation

7.1 Generate alerts for suspicious transactions
7.2 Generate alerts from fraud score thresholds
7.3 Generate alerts from rule-based anomalies
7.4 Assign alert severity

## FR-8. Case Management

8.1 Create fraud cases from alerts
8.2 Group related alerts into a case
8.3 Assign case severity
8.4 Assign case status
8.5 Allow open, investigate, and close case transitions
8.6 Allow analysts to add notes to cases
8.7 Allow analysts to assign cases to team members
8.8 Show case history
8.9 Support case search and filtering

## FR-9. Transaction Lifecycle

9.1 Track transaction lifecycle states beyond the initial decision (e.g., `AUTHORIZED` → `SETTLED`)
9.2 Make lifecycle state visible on the transaction record and dashboards

## FR-10. Reconciliation — *Out of scope (v2)*

File-based settlement ingestion, batch comparison, and reconciliation issue routing. Deferred; see Backlog v1.1 §3 for rationale.

## FR-11. Dispute Handling — *Out of scope (v2)*

Customer dispute submission and eligibility-window logic. Deferred; see Backlog v1.1 §3.

## FR-12. Chargeback Decisioning — *Out of scope (v2)*

Chargeback outcome decisioning, dependent on FR-10 and FR-11. Deferred; see Backlog v1.1 §3.

## FR-13. Back-Office Processing — *Out of scope (v2)*

Event-driven incremental back-office jobs. Deferred; see Backlog v1.1 §3.

## FR-14. Event Management — *Out of scope (v2)*

Event queue infrastructure for asynchronous back-office triggers. Deferred; see Backlog v1.1 §3.

## FR-15. Dashboard and User Interface

15.1 Display all transactions, searchable by user ID and transaction ID
15.2 Display fraud scores
15.3 Display transaction decisions
15.4 Display alerts and status
15.5 Display cases and status
15.6 Display disputed transactions *(v2 — dependent on FR-11)*
15.7 Display transaction lifecycle timelines / SLA
15.8 Provide filters by status, risk level, date, and user; display chargeback decisions *(chargeback portion is v2 — dependent on FR-12)*

## FR-16. Reports and Analytics

16.1 Generate fraud summary reports
16.2 Report total transactions processed
16.3 Report number of allowed transactions
16.4 Report number of reviewed transactions
16.5 Report number of blocked transactions
16.6 Report number of alerts generated
16.7 Report number of cases opened
16.8 Report number of disputes filed *(v2)*
16.9 Report number of chargebacks initiated *(v2)*
16.10 Report model performance metrics

## FR-17. Administration

17.1 Allow admins to configure fraud thresholds
17.2 Allow admins to configure rule thresholds
17.3 Allow admins to manage users
17.4 Allow admins to view system logs
17.5 Allow admins to enable or disable fraud rules
17.6 Allow admins to configure dispute windows *(v2)*
17.7 Allow admins to configure case severity levels
17.8 Allow admins to export system data

## FR-18. Testing and Simulation

18.1 Support demo transaction generation
18.2 Support simulated fraudulent transactions
18.3 Support simulated legitimate transactions
18.4 Allow test users to replay transaction scenarios
18.5 Allow users to test different threshold settings
18.6 Provide sample dispute scenarios *(v2)*
18.7 Provide sample reconciliation scenarios *(v2)*
18.8 Provide sample chargeback scenarios *(v2)*
18.9 Allow manual triggering of back-office jobs *(v2)*
18.10 Allow demo reset before presentation

## FR-19. Audit and Logging

19.1 Log all transaction submissions
19.2 Log fraud scoring decisions
19.3 Log alert creation
19.4 Log case updates
19.5 Log admin configuration changes
19.6 Log user activity
