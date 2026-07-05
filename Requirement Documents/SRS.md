# Software Requirements Specification (SRS)

## Project: FraudPulse End-to-End Fraud Detection System

> **Harmonization note:** Section 3.1 previously used a standalone FR-1…FR-15 numbering scheme that did not line up with the Functional Requirements document or the Backlog. It now references the canonical FR-1…FR-19 list in `Functional_Requirements.md`. See `CHANGELOG.md`.

## 1. Introduction

### 1.1 Purpose

This document defines the software requirements for FraudPulse, an end-to-end payment fraud detection system. It consolidates functional and non-functional requirements into a single implementation and validation reference.

### 1.2 Scope

FraudPulse ingests payment transactions, computes fraud risk scores, applies policy-based decisions (`ALLOW`, `REVIEW`, `BLOCK`), supports analyst investigations through alerts and case management, and provides operational dashboards. The system includes REST APIs, decision workflows, and administrative controls for fraud operations.

### 1.3 Definitions

- **ALLOW** — low-risk transaction accepted.
- **REVIEW** — transaction routed to analysts (the transaction itself is still allowed to proceed; see `System_Understanding.md` §7 for why REVIEW does not block or delay the transaction).
- **BLOCK** — transaction stopped due to high risk.

## 2. Overall Description

### 2.1 Product Perspective

FraudPulse is a modular fraud operations system composed of transaction ingestion, fraud scoring, decisioning, case management, and dashboard modules. It is designed so model, API, and database components can evolve independently while remaining operationally integrated.

### 2.2 Product Functions

- Accept and validate transaction submissions via API.
- Generate a fraud score and supporting score-explanation signals.
- Classify transactions into `ALLOW`, `REVIEW`, or `BLOCK` using configurable thresholds.
- Create, route, and track investigation cases from fraud events.
- Present analyst and admin dashboards with real-time operational metrics.
- Allow administrators to manage rules, thresholds, model versions, and role-based permissions.

### 2.3 User Characteristics

- **Customer:** may submit disputes (v2) and view the allowed scope of transaction status.
- **Fraud Analyst:** investigates alerts and cases, adds evidence, records dispositions, and performs policy-allowed overrides.
- **Administrator:** manages users, configures thresholds, model versions, validation policies, and role permissions.
- **System Integrator / API Client:** submits transaction payloads and consumes decisions for downstream processing.

### 2.4 Constraints

- Decision latency target: fraud score and decision returned within 500 ms for 95% of normal-load requests.
- Throughput target: at least 50 transactions per second under expected operating conditions.
- All protected API endpoints require valid bearer-token authentication.
- Sensitive payment-related fields must not be logged; sensitive values must be masked.
- Core APIs, decision logic, and model inference require automated tests and CI quality checks.

### 2.5 Assumptions and Dependencies

- A trained scoring model and rule configuration are available at runtime.
- Users access the platform through modern browsers and authorized clients.
- Upstream systems provide complete transaction payloads with required fields.
- Persistent data storage is available for transactions, scores, decisions, and case history.
- Operational users are provisioned and assigned valid roles before production use.
- API documentation is maintained via Swagger/OpenAPI definitions.

## 3. Specific Requirements

### 3.1 Functional Requirements

The full functional requirements list (FR-1 through FR-19) lives in **`Functional_Requirements.md`**, and is the canonical source of truth shared with the Backlog traceability matrix. Summary of in-scope areas for this release:

| FR | Area | In scope for this release? |
|---|---|---|
| FR-1 | User authentication and roles | Yes |
| FR-2 | Transaction ingestion | Yes |
| FR-3 | Fraud scoring | Yes |
| FR-4 | Real-time decision engine | Yes |
| FR-5 | Rule-based fraud detection | Yes |
| FR-6 | Watchlist management | Yes |
| FR-7 | Alert generation | Yes |
| FR-8 | Case management | Yes |
| FR-9 | Transaction lifecycle | Yes |
| FR-10 | Reconciliation | No — v2 |
| FR-11 | Dispute handling | No — v2 |
| FR-12 | Chargeback decisioning | No — v2 |
| FR-13 | Back-office processing | No — v2 |
| FR-14 | Event management | No — v2 |
| FR-15 | Dashboard and UI | Yes |
| FR-16 | Reports and analytics | Yes |
| FR-17 | Administration | Yes |
| FR-18 | Testing and simulation | Yes |
| FR-19 | Audit and logging | Yes |

### 3.2 Non-Functional Requirements

The full NFR list (NFR-1 through NFR-15) lives in **`Non_Functional_Requirements.md`**, grouped under Performance, Reliability & Fault Tolerance, Scalability, Usability, Security, Maintainability, and Documentation.

## 4. External Interface Requirements

### 4.1 API Interfaces

- Transaction ingestion API for transaction submission and validation responses.
- Scoring and decision response payload including score, decision, and metadata.
- Administrative endpoints for threshold and model version management (role-protected).
- Health endpoint for service readiness and availability checks.

### 4.2 User Interfaces

- Analyst interface for alert triage, case workflow, and investigation notes.
- Administrator interface for policy configuration, monitoring, and exports.
- Dashboard interface with operational and fraud risk metrics, filters, and drill-down.

## 5. Assumptions, Risks, and Future Enhancements

### 5.1 Assumptions

- Production deployment includes secure secret management and role provisioning processes.
- A model governance process exists for validation before model promotion.

### 5.2 Known Risks

- Data quality issues from upstream systems can reduce scoring reliability.
- False positives may increase analyst workload if thresholds are not tuned continuously.

### 5.3 Future Enhancements (v2)

- Pluggable model experimentation and champion–challenger evaluation.
- Expanded integrations for external dispute and chargeback systems (FR-10 through FR-14).
