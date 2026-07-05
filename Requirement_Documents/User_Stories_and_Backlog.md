# FraudPulse — User Stories & Product Backlog

_Version 1.2 (harmonized merge of Backlog v1.1 and User Stories & Acceptance Criteria v3)_

---

**FraudPulse**

**End-to-End Fraud Detection System**

_Product Backlog and User Stories_

_Version 1.1 | Revised Scope_

| Document title | FraudPulse Product Backlog and User Stories                 |
| -------------- | ----------------------------------------------------------- |
| Version        | 1.1                                                         |
| Status         | Revised — scope reduced for timely delivery                 |
| Owner          | Capstone team                                               |
| Sprint cadence | 6 sprints x 2 weeks                                         |
| Stories (v1.0) | 40                                                          |
| Stories (v1.1) | 37 (6 epics removed, 14 new stories added from updated FRs) |

# 1. Introduction

FraudPulse is a simulated end-to-end fraud detection platform built as an MSc Software Engineering capstone.

# 2. Document conventions

## 2.1 Story identifier

Each story carries a stable identifier of the form FP-NNN. Identifiers from v1.0 that were removed are retired and not reused.

## 2.2 Priority

- **Must** — required for delivery. Removing it makes the system incoherent.

- **Should** — important and planned; the system still functions if it slips one sprint.

- **Could** — picked up only if a sprint ends ahead of schedule.

## 2.3 Story points

Modified Fibonacci (1, 2, 3, 5, 8). Stories larger than 8 must be split before sprint planning. Points are relative effort, not hours.

## 2.4 Sprint label

Target sprint shown as S0—S6 in the story card header. Sprint 0 = foundations week; Sprints 1—6 = two weeks each.

# 3. Personas

| Persona              | Description                                                                                   | Primary surface                |
| -------------------- | --------------------------------------------------------------------------------------------- | ------------------------------ |
| Customer (simulated) | Submits transactions; may dispute (v2). Simulated by the test harness in this release.        | REST API, Simulation panel     |
| Fraud Analyst        | Monitors transactions and scores, manages alerts, owns case investigations, views watchlist.  | All analyst UI pages           |
| Customer Support     | Views cases and transaction status to assist customers. Read-only access in v1.               | Transaction Monitor, Case list |
| System Administrator | Configures thresholds, rules, and users; views logs and reports.                              | Admin panel, Reports           |
| FraudPulse System    | Automated actor: scoring, decisioning, rule evaluation, watchlist management, alert creation. | All backend modules            |
| Developer / DevOps   | Builds, tests, and deploys the platform.                                                      | CI/CD, Docker, Render          |

# 4. Epic overview

| Epic | Name                             | Stories       | Sprint(s) |
| ---- | -------------------------------- | ------------- | --------- |
| E1   | Authentication & User Management | FP-001–FP-003 | 1         |
| E2   | Transaction Ingestion            | FP-004–FP-006 | 2, 5      |
| E3   | Fraud Scoring                    | FP-007–FP-009 | 2, 3, 4   |
| E4   | Decision Engine                  | FP-010–FP-011 | 3         |
| E5   | Rule-Based Fraud Detection       | FP-012–FP-014 | 3         |
| E6   | Watchlist Management             | FP-015–FP-017 | 4, 5      |
| E7   | Alert Generation                 | FP-018–FP-020 | 4, 5      |
| E8   | Case Management                  | FP-021–FP-024 | 4, 5      |
| E9   | Transaction Lifecycle            | FP-025–FP-026 | 2, 5      |
| E10  | Dashboard and UI                 | FP-027–FP-029 | 5         |
| E11  | Reports and Analytics            | FP-030        | 6         |
| E12  | Administration                   | FP-031–FP-032 | 3, 6      |
| E13  | Testing and Simulation           | FP-033–FP-034 | 6         |
| E14  | Platform and DevOps              | FP-035–FP-037 | 0, 2, 6   |

# 5. User stories

Stories are presented epic by epic. Each story card is self-contained and includes acceptance criteria sufficient to declare it Done.

## 5.1 Epic E1 — Authentication and User Management

### FP-001 — User login and session management

**Priority:** Must | **3 pts | S1**

**Story:** As a user, I want to log in with my credentials and maintain a secure session, so that only authorised personnel can access FraudPulse.

**Acceptance criteria:**

**1.** Given valid credentials, the system issues a session token and redirects to the default landing page.

**2.** Given invalid credentials, the system returns a clear error and does not issue a token.

**3.** Sessions expire after a configurable idle period (default 30 minutes); the user is prompted to re-authenticate.

**4.** All login attempts (success and failure) are written to the activity log with timestamp and source IP.

**Primary persona:** All roles | Functional req:\*\* FR-1.1, FR-1.5

### FP-002 — Role-based access control

**Priority:** Must | **3 pts | S1**

**Story:** As FraudPulse, I want to restrict feature access based on the authenticated user's role, so that least-privilege is enforced across all system surfaces.

**Acceptance criteria:**

**1.** Five roles are defined: Customer, Fraud Analyst, Customer Support, System Administrator, and FraudPulse System.

**2.** Each API endpoint and UI route enforces role checks; unauthorised access returns HTTP 403.

**3.** Role assignments are stored in the database; changes take effect on the next request without requiring a redeploy.

**4.** A role-permission matrix is documented in the system design document and is enforced automatically.

**Primary persona:** System Administrator | Functional req:\*\* FR-1.2, FR-1.3, FR-1.4

### FP-003 — Admin user and role management

**Priority:** Must | **2 pts | S1**

**Story:** As a system administrator, I want to create, deactivate, and reassign roles for users, so that team membership changes are reflected immediately.

**Acceptance criteria:**

**1.** An admin can create a user with a specified role and temporary password.

**2.** An admin can deactivate a user; deactivated users cannot log in but their history is preserved.

**3.** An admin can change a user's role; the change is logged with the admin's identity and timestamp.

**4.** User management actions are visible in the admin activity log.

**Primary persona:** System Administrator | Functional req:\*\* FR-1.6, FR-17.3

## 5.2 Epic E2 — Transaction Ingestion

### FP-004 — Submit transaction via REST API

**Priority:** Must | **3 pts | S2**

**Story:** As a customer, I want to submit a payment transaction to FraudPulse and receive an authorization decision, so that my purchase can proceed without unnecessary delay.

**Acceptance criteria:**

**1.** POST /transactions accepts: transaction ID, user ID, amount, currency, timestamp, merchant, user public IP, and optional device or location data.

**2.** The API returns a JSON response containing the transaction ID, fraud score, and decision (ALLOW, ALLOW_WITH_REVIEW, or BLOCK) within 500 ms for the 95th percentile of test traffic.

**3.** The transaction is persisted before the response is returned; the caller never receives a decision for a record that was not stored.

**4.** Submitting a transaction ID that already exists returns HTTP 409 with a clear error body.

**Primary persona:** Customer (simulated) | Functional req:\*\* FR-2.1, FR-2.2

### FP-005 — Validate and reject invalid transactions

**Priority:** Must | **2 pts | S2**

**Story:** As FraudPulse, I want to validate every incoming transaction payload, so that malformed data does not reach the scoring pipeline.

**Acceptance criteria:**

**1.** Required fields (transaction ID, user ID, amount, timestamp, merchant) must be present and correctly typed; violations return HTTP 400 with per-field errors.

**2.** Amount must be a positive number; timestamp must be ISO-8601 and not more than 24 hours in the future.

**3.** Both valid and invalid submissions are stored — valid ones in the transactions table, invalid ones in a rejected-requests log — so the full submission history is auditable.

**4.** Duplicate transaction IDs are detected and rejected with HTTP 409 before reaching the scoring pipeline.

**Primary persona:** System | Functional req:\*\* FR-2.3, FR-2.4, FR-2.5

### FP-006 — Manual transaction entry from the UI

**Priority:** Should | **2 pts | S5**

**Story:** As a fraud analyst or administrator, I want to enter a transaction manually through the UI, so that test scenarios and edge cases can be submitted without writing API calls.

**Acceptance criteria:**

**1.** The UI provides a form with all required transaction fields and submits to the same POST /transactions endpoint.

**2.** Validation errors from the API are displayed inline next to the relevant fields.

**3.** On success, the user is redirected to the new transaction's detail view.

**4.** A note field on the manual form is stored as a transaction annotation to distinguish manual entries from API submissions.

**Primary persona:** Admin | Functional req:\*\* FR-2.6

## 5.3 Epic E3 — Fraud Scoring

### FP-007 — Compute fraud risk score

**Priority:** Must | **5 pts | S2**

**Story:** As FraudPulse, I want to compute a fraud probability score for every valid transaction, so that downstream decisioning has a reliable, data-driven signal.

**Acceptance criteria:**

**1.** A trained model artifact is loaded at service start-up; a missing or corrupt artifact causes a fast-fail startup error.

**2.** Feature engineering applies the same transformations used at training time; schema mismatches cause a startup error, not a per-request failure.

**3.** Scoring returns a probability between 0 and 1 (at least 4 decimal places), stored alongside the transaction.

**4.** Each score record includes: transaction ID, score value, model version string, and scoring timestamp.

**5.** If scoring fails at runtime, the transaction is marked ALLOW_WITH_REVIEW, the error is logged, and a fallback alert is raised.

**Primary persona:** System | Functional req:\*\* FR-3.1, FR-3.2, FR-3.3, FR-3.4, FR-3.8

### FP-008 — Re-run scoring on selected transactions

**Priority:** Should | **2 pts | S4**

**Story:** As a fraud analyst, I want to re-score one or more selected transactions, so that I can validate the effect of a model or threshold change without reprocessing everything.

**Acceptance criteria:**

**1.** The analyst selects one or more transactions from the UI and triggers a rescore.

**2.** Rescoring runs synchronously for up to 10 transactions; larger batches are queued and the analyst is notified on completion.

**3.** Each rescore creates a new score record; the original score is preserved and both are visible in the transaction detail.

**4.** Rescore events are written to the transaction audit history.

**Primary persona:** Fraud Analyst | Functional req:\*\* FR-3.5, FR-3.6

### FP-009 — Score explanation for flagged transactions

**Priority:** Should | **3 pts | S3**

**Story:** As a fraud analyst, I want to see the top contributing features for a flagged transaction's score, so that I can assess whether the decision is appropriate.

**Acceptance criteria:**

**1.** Up to five reason codes are returned per transaction, each with a feature name, contribution direction (HIGH / LOW risk), and a contribution magnitude.

**2.** Rule-triggered reasons are listed separately from model feature contributions.

**3.** If no explanation can be generated, the field is present but empty and a warning is logged; the UI displays a neutral message.

**4.** Explanations are visible in both the API response and the transaction detail panel.

**Primary persona:** Fraud Analyst | Functional req:\*\* FR-3.7

## 5.4 Epic E4 — Decision Engine

### FP-010 — ALLOW, ALLOW_WITH_REVIEW, and BLOCK classification

**Priority:** Must | **3 pts | S3**

**Story:** As FraudPulse, I want to translate every fraud score into one of three decisions using configurable thresholds, so that responses are consistent and auditable.

**Acceptance criteria:**

**1.** Default thresholds: ALLOW below 0.40, ALLOW_WITH_REVIEW from 0.40 to 0.79 inclusive, BLOCK at 0.80 or above.

**2.** The decision is stored on the transaction record and returned in the API response.

**3.** A decision audit record captures the threshold values that were active at the time of the decision.

**4.** ALLOW_WITH_REVIEW transactions are automatically added to the watchlist; BLOCK transactions raise an immediate alert.

**Primary persona:** System | Functional req:\*\* FR-4.1, FR-4.2, FR-4.3, FR-4.5, FR-4.6

### FP-011 — Configure decision thresholds

**Priority:** Must | **2 pts | S3**

**Story:** As an administrator, I want to configure the ALLOW/ALLOW_WITH_REVIEW/BLOCK score thresholds, so that the sensitivity of the decision engine can be tuned without a code change.

**Acceptance criteria:**

**1.** An admin-only endpoint and UI form accept new threshold values for the ALLOW_WITH_REVIEW and BLOCK boundaries.

**2.** The system rejects invalid threshold configurations (e.g., ALLOW_WITH_REVIEW boundary ≥ BLOCK boundary).

**3.** New thresholds take effect on the next scored transaction without a redeploy.

**4.** Every threshold change is logged with the admin's identity, timestamp, and old/new values (see FP-032).

**Primary persona:** System Administrator | Functional req:\*\* FR-4.4, FR-4.7

## 5.5 Epic E5 — Rule-Based Fraud Detection

### FP-012 — Detect transaction anomalies via rules

**Priority:** Must | **3 pts | S3**

**Story:** As FraudPulse, I want to apply a set of explicit fraud rules to every transaction, so that obvious anomalies are caught even when the model score is below the threshold.

**Acceptance criteria:**

**1.** Rules include at minimum: amount above a configurable per-user limit, transaction velocity above a threshold in a rolling time window, and detection of duplicate transactions.

**2.** A triggered rule raises the effective decision to at least ALLOW_WITH_REVIEW regardless of the model score.

**3.** Each triggered rule is stored as a rule-trigger record linked to the transaction.

**4.** Rule trigger results are included in the transaction's score explanation.

**Primary persona:** System | Functional req:\*\* FR-5.1, FR-5.2, FR-5.3, FR-5.7, FR-5.9

### FP-013 — Detect suspicious location and merchant

**Priority:** Should | **2 pts | S3**

**Story:** As FraudPulse, I want to flag transactions from risky merchants or unusual locations, so that contextual risk signals supplement the model score.

**Acceptance criteria:**

**1.** Rules detect: transactions from merchants on the risky-merchant list, transactions from users on the flagged-user watchlist, and significant location changes between consecutive transactions.

**2.** Each contextual flag is stored as a rule trigger and included in the explanation.

**3.** Merchant and flagged-user lists are configurable by an admin without a code change.

**4.** Contextual flags follow the same escalation logic as other rules (at least ALLOW_WITH_REVIEW).

**Primary persona:** System | Functional req:\*\* FR-5.4, FR-5.5, FR-5.6

### FP-014 — Enable and disable fraud rules

**Priority:** Should | **2 pts | S3**

**Story:** As an administrator, I want to enable or disable individual fraud rules, so that noisy or low-value rules can be turned off without a deployment.

**Acceptance criteria:**

**1.** Each rule from FP-012 and FP-013 has an admin-controlled enabled/disabled flag.

**2.** Disabled rules are skipped during scoring and clearly marked as inactive in the admin panel.

**3.** Changing a rule's status is logged with the admin's identity and timestamp.

**4.** Disabling a rule does not affect historical rule-trigger records already stored.

**Primary persona:** System Administrator | Functional req:\*\* FR-5.8, FR-17.5

## 5.6 Epic E6 — Watchlist Management

### FP-015 — Add transactions and entities to the watchlist

**Priority:** Must | **3 pts | S4**

**Story:** As FraudPulse, I want to automatically add high-risk and medium-risk merchants to the appropriate watchlist, so that they receive heightened scrutiny on future activity.

**Acceptance criteria:**

**1.** BLOCK decisions add the transaction to the blacklist; ALLOW_WITH_REVIEW decisions add it to the watchlist with the triggering reason.

**2.** Users and merchants can be placed on the watchlist manually by an analyst or automatically when multiple BLOCK decisions are linked to them.

**3.** Each watchlist entry stores: entity type (transaction, user, merchant), entity ID, reason, severity, added-by, and an expiry timestamp (default 30 days, configurable).

**4.** Future transactions from watchlisted users or merchants trigger the contextual-risk rule in FR-5.

**Primary persona:** System / Fraud Analyst | Functional req:\*\* FR-5.1, FR-5.2, FR-5.5, FR-5.6

### FP-016 — View and manage the watchlist

**Priority:** Must | **2 pts | S5**

**Story:** As a fraud analyst, I want to view all watchlisted entities, filter by type and severity, and remove entries when appropriate, so that the watchlist remains accurate and actionable.

**Acceptance criteria:**

**1.** The watchlist view shows: entity ID, type, reason, severity, added-by, added-at, and days until expiry.

**2.** Filters by entity type (transaction, user, merchant) and severity are supported.

**3.** An analyst can remove an entry with a mandatory justification note that is stored in the watchlist history.

**4.** Expired entries are removed by a nightly job and are visible in the history view.

**Primary persona:** Fraud Analyst | Functional req:\*\* FR-5.3, FR-5.4, FR-5.7

### FP-017 — Maintain watchlist change history

**Priority:** Should | **1 pts | S4**

**Story:** As FraudPulse, I want to record every addition, modification, and removal from the watchlist, so that the watchlist history is fully auditable.

**Acceptance criteria:**

**1.** Each watchlist change creates a history record with: entity ID, action (ADDED, REMOVED, EXPIRED), reason, actor, and timestamp.

**2.** History records are immutable and cannot be deleted through the application.

**3.** The watchlist history is searchable by entity ID and date range.

**4.** History is visible from the watchlist entry detail view.

**Primary persona:** System | Functional req:\*\* FR-5.8

## 5.7 Epic E7 — Alert Generation

### FP-018 — Generate alerts from scores and rules

**Priority:** Must | **3 pts | S4**

**Story:** As FraudPulse, I want to generate an alert whenever a transaction's score or a triggered rule warrants analyst attention, so that suspicious activity surfaces in the alert queue.

**Acceptance criteria:**

**1.** An alert is created for every ALLOW_WITH_REVIEW and BLOCK decision and for every rule trigger on an ALLOW transaction that came close to the threshold.

**2.** Each alert contains: alert ID, transaction ID, reason, severity (LOW, MEDIUM, HIGH), status (NEW, ACKNOWLEDGED, RESOLVED), created-at, and resolved-at.

**3.** Duplicate alerts for the same transaction within a configurable suppression window are collapsed into one.

**4.** Alert creation and resolution timestamps are stored and visible in the alert detail.

**Primary persona:** System | Functional req:\*\* FR-7.1, FR-7.2, FR-7.3, FR-7.4, FR-7.8

## 5.8 Epic E8 — Case Management

### FP-019 — Create and view cases

**Priority:** Must | **3 pts | S4**

**Story:** As a fraud analyst, I want to create, search, and view fraud investigation cases, so that I have a single place to track each investigation from start to finish.

**Acceptance criteria:**

**1.** Cases are created from alerts (via FP-020, remapped to FP-022 in this harmonization) or manually from the case list.

**2.** Each case stores: case ID, title, status (OPEN, INVESTIGATING, CLOSED), risk level (LOW, MEDIUM, HIGH), linked alerts, linked transactions, notes, timeline, and timestamps.

**3.** The case list supports search by case ID and title, and filters by status and risk level.

**4.** Cases are ordered by risk level then age by default.

**Primary persona:** Fraud Analyst | Functional req:\*\* FR-8.1, FR-8.2, FR-8.3, FR-8.4, FR-8.9

### FP-020 — Case detail view

**Priority:** Must | **3 pts | S5**

**Story:** As a fraud analyst, I want to see all transactions, alerts, and events linked to a case in one view, so that I have full context during an investigation.

**Acceptance criteria:**

**1.** The detail view shows linked transactions (ID, amount, score, decision, lifecycle status) and linked alerts (reason, severity, status).

**2.** A chronological timeline shows all case events: alert added, status changed, note added, assignment changed.

**3.** An aggregate risk indicator combines the highest linked score, alert count, and case age.

**4.** The view loads in under 2 seconds for cases with up to 50 linked items.

**Primary persona:** Fraud Analyst | Functional req:\*\* FR-8.5, FR-8.8

### FP-021 — Case status workflow and assignment

**Priority:** Must | **2 pts | S4**

**Story:** As a fraud analyst, I want to transition cases through OPEN, INVESTIGATING, and CLOSED and assign them to team members, so that work is distributed and tracked.

**Acceptance criteria:**

**1.** Status transitions follow the state machine: OPEN → INVESTIGATING → CLOSED; invalid transitions are rejected with a clear error.

**2.** Closing a case requires a resolution code (CONFIRMED_FRAUD, FALSE_POSITIVE, INCONCLUSIVE).

**3.** An analyst can assign a case to any active user with the Fraud Analyst role.

**4.** All status and assignment changes are written to the case timeline.

**Primary persona:** Fraud Analyst | Functional req:\*\* FR-8.5, FR-8.7

### FP-022 — Add notes to cases

**Priority:** Should | **1 pts | S5**

**Story:** As a fraud analyst, I want to add timestamped notes to a case, so that other team members can follow the investigation thread.

**Acceptance criteria:**

**1.** Notes are append-only: once saved they cannot be edited or deleted.

**2.** Each note records author, timestamp, and body (max 2,000 characters).

**3.** Notes are displayed on the case timeline in chronological order.

**4.** An empty note submission is prevented at both UI and API level.

**Primary persona:** Fraud Analyst | Functional req:\*\* FR-8.6

## 5.9 Epic E9 — Dashboard and UI

### FP-023 — Transaction monitor

**Priority:** Must | **3 pts | S5**

**Story:** As a fraud analyst, I want a paginated, filterable view of all transactions with their fraud scores and decisions, so that I can quickly identify suspicious activity.

**Acceptance criteria:**

**1.** The table shows: timestamp, transaction ID, user ID, merchant, amount, score, decision, and lifecycle status, ordered by timestamp descending.

**2.** Filters by decision (ALLOW/ALLOW_WITH_REVIEW/BLOCK), user ID, score range, and date range are available and combinable.

**3.** Selecting a row opens a detail panel showing the full transaction, score explanation, and lifecycle timeline.

**4.** Pagination defaults to 25 rows per page with options for 10, 25, and 50.

**Primary persona:** Fraud Analyst | Functional req:\*\* FR-15.1, FR-15.2, FR-15.3, FR-15.8

### FP-024 — Alert and case dashboard

**Priority:** Must | **2 pts | S5**

**Story:** As a fraud analyst, I want a single dashboard view of open alerts and active cases, so that I can prioritise my work each day.

**Acceptance criteria:**

**1.** The dashboard shows: count of NEW alerts by severity, count of open cases by risk level, and the 10 most recent unacknowledged alerts.

**2.** Each alert and case entry is a link to the relevant detail view.

**3.** The view refreshes automatically every 30 seconds.

**4.** Filters by severity and date range apply to both sections simultaneously.

**Primary persona:** Fraud Analyst | Functional req:\*\* FR-15.4, FR-15.5

### FP-025 — System metrics summary

**Priority:** Should | **2 pts | S5**

**Story:** As a fraud analyst or administrator, I want a metrics summary card showing transaction volumes and decision splits, so that I can monitor system posture at a glance.

**Acceptance criteria:**

**1.** The summary shows: transactions processed in the last hour and 24 hours, decision breakdown (ALLOW/ALLOW_WITH_REVIEW/BLOCK count and percentage), active cases, and score mean and median.

**2.** Metrics are computed from database queries and return in under 500 ms.

**3.** If the database is unavailable, the panel shows a clear staleness warning.

**4.** Data refreshes automatically every 60 seconds.

**Primary persona:** Fraud Analyst / Admin | Functional req:\*\* FR-15.7

## 5.10 Epic E10 — Reports and Analytics

### FP-026 — Fraud summary report

**Priority:** Should | **3 pts | S6**

**Story:** As a fraud analyst or administrator, I want to generate a fraud summary report for a selected date range, so that I can present outcomes to stakeholders.

**Acceptance criteria:**

**1.** The report includes: total transactions, counts and percentages for ALLOW/ALLOW_WITH_REVIEW/BLOCK decisions, alerts generated, cases opened and closed, and model performance metrics (precision and recall from offline evaluation).

**2.** The report is downloadable as CSV.

**3.** Date range, decision filter, and user filter are configurable before generation.

**4.** Report generation for up to 30 days of data completes within 10 seconds.

**Primary persona:** Fraud Analyst / Admin | Functional req:\*\* FR-15.1 to FR-15.7, FR-15.10

## 5.11 Epic E11 — Administration

### FP-027 — Admin configuration panel

**Priority:** Must | **2 pts | S3**

**Story:** As a system administrator, I want a single admin panel to configure fraud thresholds, rule settings, and case severity levels, so that operational tuning does not require code changes.

**Acceptance criteria:**

**1.** The panel allows editing: ALLOW/ALLOW_WITH_REVIEW/BLOCK score thresholds, per-rule enable/disable toggles, rule-specific parameters (e.g., velocity window in minutes, high-amount limit), and case severity level definitions.

**2.** Invalid configurations (overlapping thresholds, negative limits) are rejected with field-level errors.

**3.** All configuration changes are written to the admin audit log.

**4.** A "PALLOW_WITH_REVIEW" mode allows an admin to see how existing transactions would be reclassified under proposed thresholds before applying.

**Primary persona:** System Administrator | Functional req:\*\* FR-17.1, FR-17.2, FR-17.5, FR-17.7

### FP-028 — System logs and audit trail

**Priority:** Should | **2 pts | S6**

**Story:** As a system administrator, I want searchable structured logs and an immutable audit trail for all key business events, so that the system's behaviour is traceable after the fact.

**Acceptance criteria:**

**1.** Application logs are JSON-formatted and include: request ID, transaction ID (where applicable), user ID, severity, and timestamp.

**2.** The audit trail captures: all transaction submissions, scoring decisions, alert creation and resolution, case updates, admin configuration changes, and user login/logout events.

**3.** Logs and audit records are searchable by transaction ID, user ID, event type, and date range from the admin panel.

**4.** Audit records are append-only and cannot be modified or deleted through the application.

**Primary persona:** System Administrator | Functional req:\*\* FR-17.4, FR-19.1 to FR-19.10

## 5.12 Epic E12 — Testing and Simulation

### FP-029 — Generate demo transactions

**Priority:** Must | **2 pts | S6**

**Story:** As a fraud analyst or administrator, I want to generate synthetic legitimate and fraudulent transactions, so that I can demonstrate the system and test different threshold configurations.

**Acceptance criteria:**

**1.** The simulation panel allows generating a configurable number of transactions (1—100) with a selectable fraud ratio.

**2.** Simulated transactions use realistic merchant names, amounts, and user IDs drawn from a fixture dataset.

**3.** After generation, the user can change the active threshold and see how decisions change on the same batch.

**4.** Generated transactions are labelled as SIMULATED in the transactions table so they are distinguishable from real submissions.

**Primary persona:** Fraud Analyst / Admin | Functional req:\*\* FR-18.1, FR-18.2, FR-18.3, FR-18.4, FR-18.5

### FP-030 — Demo reset

**Priority:** Should | **1 pts | S6**

**Story:** As a system administrator, I want to reset the system to a clean state before a presentation, so that historical test data does not interfere with the demo.

**Acceptance criteria:**

**1.** A "Reset Demo Data" action in the admin panel removes all SIMULATED transactions, their alerts, and any cases that contain only simulated transactions.

**2.** The reset does not affect non-simulated data or system configuration.

**3.** The action requires a confirmation step to prevent accidental execution.

**4.** Completion is confirmed with a summary: rows removed per table.

**Primary persona:** System Administrator | Functional req:\*\* FR-18.10

## 5.13 Epic E13 — Platform and DevOps

### FP-031 — CI/CD pipeline

**Priority:** Must | **2 pts | S0**

**Story:** As a developer, I want automated linting and tests to run on every push, so that regressions are caught before they reach the main branch.

**Acceptance criteria:**

**1.** GitHub Actions runs on push to any branch and on pull requests targeting main.

**2.** Pipeline stages: lint (ruff / eslint), unit tests (pytest / jest), and build verification.

**3.** Failure on any stage blocks the merge.

**4.** Pipeline status badges are displayed in the project README.

**Primary persona:** Developer | Functional req:\*\* DevOps

### FP-032 — Containerised deployment

**Priority:** Must | **3 pts | S6**

**Story:** As a developer, I want the backend fully containerised, so that any team member can run the system locally and deploy to Render with one command.

**Acceptance criteria:**

**1.** A docker-compose configuration brings up API, Angular UI, and PostgreSQL together.

**2.** Images build from a clean checkout with no host-specific paths.

**3.** Environment configuration is driven exclusively by .env files; no secrets are committed.

**4.** A README section documents local setup and Render deployment steps.

**Primary persona:** Developer | Functional req:\*\* DevOps

### FP-033 — Auto-generated API documentation

**Priority:** Should | **1 pts | S2**

**Story:** As a developer, I want interactive Swagger documentation auto-generated by FastAPI, so that the API contract is always up to date without manual effort.

**Acceptance criteria:**

**1.** /docs is reachable and lists every public endpoint with request schema, response schema, and at least one example.

**2.** The Swagger spec is exported as a static OpenAPI JSON file as part of the CI build.

**3.** Endpoints without docstrings cause a CI warning.

**4.** Authentication-protected endpoints are clearly marked in the Swagger UI.

**Primary persona:** Developer | Functional req:\*\* DevOps

# 6. Sprint allocation summary

The table shows how stories map to sprints. Rebalance after each retrospective.

| Sprint   | Theme                     | Goal                                                                                          | Stories                                                                                |
| -------- | ------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Sprint 0 | Foundations               | Repo, branching, CI pipeline, project board.                                                  | FP-035                                                                                 |
| Sprint 1 | Auth & ML Baseline        | Login, RBAC, user management, and the trained fraud model artifact.                           | FP-001, FP-002, FP-003 + ML model                                                      |
| Sprint 2 | Transaction API           | /transactions endpoint, validation, storage, fraud scoring, lifecycle.                        | FP-004, FP-005, FP-007, FP-025, FP-037                                                 |
| Sprint 3 | Decision & Rules          | Decision engine, thresholds, rule-based detection, admin config, explainability.              | FP-009, FP-010, FP-011, FP-012, FP-013, FP-014, FP-031                                 |
| Sprint 4 | Watchlist, Alerts & Cases | Watchlist, alert generation, case creation, rescore, lifecycle detail.                        | FP-008, FP-015, FP-017, FP-018, FP-020, FP-021, FP-023                                 |
| Sprint 5 | UI                        | All analyst-facing Angular pages: transactions, alerts, cases, watchlist, dashboard, metrics. | FP-006, FP-016, FP-019, FP-022, FP-024, FP-025(settle), FP-026, FP-027, FP-028, FP-029 |
| Sprint 6 | Polish & Deploy           | Reports, simulation, demo reset, audit logs, Docker, Render deployment.                       | FP-030, FP-032, FP-033, FP-034, FP-036                                                 |

# 7. Traceability matrix

Maps every functional requirement (FR-1 through FR-19) to the stories that satisfy it. Requirements marked "Out of scope (v2)" have no stories in this release.

| Requirement | Description                                | Stories                                |
| ----------- | ------------------------------------------ | -------------------------------------- |
| FR-1        | Auth & roles                               | FP-001, FP-002, FP-003                 |
| FR-2        | Transaction ingestion                      | FP-004, FP-005, FP-006                 |
| FR-3        | Fraud scoring                              | FP-007, FP-008, FP-009                 |
| FR-4        | Real-time decision engine                  | FP-010, FP-011                         |
| FR-5        | Rule-based fraud detection                 | FP-012, FP-013, FP-014                 |
| FR-6        | Watchlist management                       | FP-015, FP-016, FP-017                 |
| FR-7        | Alert generation                           | FP-018, FP-019, FP-020                 |
| FR-8        | Case management                            | FP-020, FP-021, FP-022, FP-023, FP-024 |
| FR-9        | Transaction lifecycle (AUTHORIZED/SETTLED) | FP-025, FP-026                         |
| FR-10       | Reconciliation                             | Out of scope (v2)                      |
| FR-11       | Dispute handling                           | Out of scope (v2)                      |
| FR-12       | Chargeback decisioning                     | Out of scope (v2)                      |
| FR-13       | Back-office processing                     | Out of scope (v2)                      |
| FR-14       | Event management                           | Out of scope (v2)                      |
| FR-15       | Dashboard and UI                           | FP-027, FP-028, FP-029                 |
| FR-16       | Reports and analytics                      | FP-030                                 |
| FR-17       | Administration                             | FP-003, FP-011, FP-031, FP-032         |
| FR-18       | Testing and simulation                     | FP-033, FP-034                         |
| FR-19       | Audit and logging                          | FP-032                                 |

# 8. Definition of Ready

A story may enter sprint planning only when all of the following are true.

- The story has a stable FP-NNN identifier and a clear, unambiguous title.

- The story narrative follows the As a / I want / So that pattern and names a primary persona.

- Acceptance criteria are written, testable, and number between three and five.

- Dependencies on other stories or external artefacts are documented.

- The story is estimated in story points.

- The team agrees the story fits within a single sprint.

# 9. Definition of Done

A story is Done only when every item below is true. Done is a binary state.

- Code is merged to the main branch via a ALLOW_WITH_REVIEWed pull request.

- All acceptance criteria are demonstrated in the sprint ALLOW_WITH_REVIEW or covered by automated tests.

- Unit tests cover the new behaviour and the full test suite passes in CI.

- Linting passes with no new warnings.

- Public APIs are documented in Swagger; README updated for new commands or configuration.

- Any new configuration variable has a default value and is documented.

- The story is closed on the project board with a link to the merged pull request.

# Appendix A. Backlog at a glance

All 37 stories with priority, points, and target sprint.

| ID     | Title                                              | Priority | Points | Sprint |
| ------ | -------------------------------------------------- | -------- | ------ | ------ |
| FP-001 | User login and session management                  | Must     | 3      | 1      |
| FP-002 | Role-based access control                          | Must     | 3      | 1      |
| FP-003 | Admin user and role management                     | Must     | 2      | 1      |
| FP-004 | Submit transaction via REST API                    | Must     | 3      | 2      |
| FP-005 | Validate and reject invalid transactions           | Must     | 2      | 2      |
| FP-006 | Manual transaction entry from the UI               | Should   | 2      | 5      |
| FP-007 | Compute fraud risk score                           | Must     | 5      | 2      |
| FP-008 | Re-run scoring on selected transactions            | Should   | 2      | 4      |
| FP-009 | Score explanation for flagged transactions         | Should   | 3      | 3      |
| FP-010 | ALLOW, ALLOW_WITH_REVIEW, and BLOCK classification | Must     | 3      | 3      |
| FP-011 | Configure decision thresholds                      | Must     | 2      | 3      |
| FP-012 | Detect transaction anomalies via rules             | Must     | 3      | 3      |
| FP-013 | Detect suspicious location, device, and merchant   | Should   | 2      | 3      |
| FP-014 | Enable and disable fraud rules                     | Should   | 2      | 3      |
| FP-015 | Add transactions and entities to the watchlist     | Must     | 3      | 4      |
| FP-016 | View and manage the watchlist                      | Must     | 2      | 5      |
| FP-017 | Maintain watchlist change history                  | Should   | 1      | 4      |
| FP-018 | Generate alerts from scores and rules              | Must     | 3      | 4      |
| FP-019 | Alert queue management                             | Must     | 2      | 5      |
| FP-020 | Escalate alerts to cases                           | Must     | 2      | 4      |
| FP-021 | Create and view cases                              | Must     | 3      | 4      |
| FP-022 | Case detail view                                   | Must     | 3      | 5      |
| FP-023 | Case status workflow and assignment                | Must     | 2      | 4      |
| FP-024 | Add notes to cases                                 | Should   | 1      | 5      |
| FP-025 | Track transaction lifecycle                        | Must     | 2      | 2      |
| FP-026 | View transaction lifecycle history                 | Should   | 1      | 5      |
| FP-027 | Transaction monitor                                | Must     | 3      | 5      |
| FP-028 | Alert and case dashboard                           | Must     | 2      | 5      |
| FP-029 | System metrics summary                             | Should   | 2      | 5      |
| FP-030 | Fraud summary report                               | Should   | 3      | 6      |
| FP-031 | Admin configuration panel                          | Must     | 2      | 3      |
| FP-032 | System logs and audit trail                        | Should   | 2      | 6      |
| FP-033 | Generate demo transactions                         | Must     | 2      | 6      |
| FP-034 | Demo reset                                         | Should   | 1      | 6      |
| FP-035 | CI/CD pipeline                                     | Must     | 2      | 0      |
| FP-036 | Containerised deployment                           | Must     | 3      | 6      |
| FP-037 | Auto-generated API documentation                   | Should   | 1      | 2      |

_End of document._

---

# Appendix B. Quick-Reference User Stories (from v3)

_A concise, epic-level view of the same system, originally maintained as a standalone companion document. Each story below maps to one or more epics/stories in the detailed backlog above._

## US-1 Transaction Ingestion — _maps to Epic E2 (FP-004–FP-006)_

**User Story:** As a System, I want to validate and store incoming transactions so only complete and usable data enters fraud processing.

**Acceptance Criteria:**

- **AC-1:** Given all required fields are present, when a transaction is submitted, then it is accepted and assigned a unique transaction ID.
- **AC-2:** Given required fields are missing or invalid, when validation runs, then the request is rejected with clear error details.
- **AC-3:** Given a valid transaction is accepted, when ingestion completes, then the record is available to fraud scoring.

## US-2 Fraud Scoring — _maps to Epic E3 (FP-007–FP-009)_

**User Story:** As a System, I want to score each valid transaction so fraud risk is evaluated consistently in near real time.

**Acceptance Criteria:**

- **AC-1:** Given a valid transaction, when scoring executes, then a risk score is generated and stored with model version metadata.
- **AC-2:** Given scoring succeeds, when analysts view a transaction, then they can see score and key risk signals.
- **AC-3:** Given scoring fails, when fallback rules apply, then the transaction is routed to ALLOW_WITH_REVIEW and the failure is logged.

## US-3 Decision Engine — _maps to Epic E4 (FP-010, FP-011)_

**User Story:** As a System, I want to classify transactions as ALLOW, ALLOW_WITH_REVIEW, or BLOCK so response actions are timely and policy-aligned.

**Acceptance Criteria:**

- **AC-1:** Given a score below the allow threshold, when decisioning runs, then the transaction outcome is ALLOW.
- **AC-2:** Given a score between configured thresholds, when decisioning runs, then the outcome is ALLOW_WITH_REVIEW.
- **AC-3:** Given a score above block threshold, when decisioning runs, then the outcome is BLOCK and an alert is raised.

## US-4 Case Management — _maps to Epic E8 (FP-021–FP-024)_

**User Story:** As an Analyst, I want linked investigation cases so I can track alerts, evidence, and resolution in one workflow.

**Acceptance Criteria:**

- **AC-1:** Given related alerts exist, when case rules match, then a case is created and linked to relevant transactions.
- **AC-2:** Given an open case, when an analyst adds notes or evidence, then the history is saved and auditable.
- **AC-3:** Given a case is resolved, when it is closed, then final disposition and outcome are recorded.

## US-5 Dashboard and Monitoring — _maps to Epic E10 (FP-027–FP-029)_

**User Story:** As an Admin, I want live operational and fraud dashboards so I can monitor system health and risk posture.

**Acceptance Criteria:**

- **AC-1:** Given active transaction processing, when dashboards refresh, then volume, scoring, and decision KPIs are updated.
- **AC-2:** Given filter selections are applied, when views update, then metrics and lists remain consistent with filters.
- **AC-3:** Given KPIs breach configured limits, when monitoring runs, then issues are visibly highlighted for intervention.

## US-6 Access and Audit — _maps to Epics E1 and E12 (FP-001–FP-003, FP-031, FP-032)_

**User Story:** As an Admin, I want role-based access and audit trails so high-impact actions remain controlled and traceable.

**Acceptance Criteria:**

- **AC-1:** Given role policy is configured, when a user attempts a restricted action, then only authorized roles are allowed.
- **AC-2:** Given a manual override or policy change occurs, when the action is saved, then user, timestamp, and reason are logged.
- **AC-3:** Given an audit ALLOW_WITH_REVIEW is requested, when logs are queried, then complete action history is available.
