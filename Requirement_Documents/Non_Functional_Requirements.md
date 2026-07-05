# FraudPulse — Non-Functional Requirements (NFRs)

## Performance

**NFR-1: API Latency**
The system shall return a fraud score and decision for a transaction request within 500 ms for 95% of requests under normal load.

**NFR-2: Throughput**
The system shall handle at least 50 transactions per second without failure or significant degradation.

**NFR-3: Dashboard Responsiveness**
Dashboard views (transactions, alerts, cases) shall load within 2 seconds for data up to 10,000 records.

## Reliability & Fault Tolerance

**NFR-4: Failure Handling**
If model inference does not complete within a configurable timeout (e.g., 5 seconds) or returns an error, the system shall default to a `REVIEW` decision and log the failure without crashing the API.

**NFR-5: Data Integrity**
All transaction writes shall be atomic, ensuring no partial or inconsistent records are stored.

## Scalability

**NFR-6: Scalable Architecture**
The system components (API, model, database) shall be designed with low coupling and high cohesion to allow future scaling.

## Usability

**NFR-7: Response Information**
All API and user-interface errors shall return clear, structured, and human-readable messages.

## Security

**NFR-8: Basic Access Control**
All protected API endpoints shall require authentication using a bearer token with a defined expiration time. Requests with missing, invalid, or expired tokens shall be rejected.

**NFR-9: Input Validation**
All API inputs shall be validated to prevent malformed or invalid data from entering the system.

**NFR-10: Payment Industry Standards Compliance**
The system shall not log sensitive fields. All sensitive information shall be masked.

## Maintainability

**NFR-11: Code Quality**
All code shall pass linting and formatting checks enforced via CI.

**NFR-12: Test Coverage**
Core modules (API, decision logic, model inference) shall have unit test coverage.

**NFR-13: Event Logging**
The system shall produce structured logs of events, user actions, and errors.

**NFR-14: Health Check Endpoint**
A `/health` endpoint shall indicate system availability.

## Documentation

**NFR-15: API Documentation**
API endpoints shall be documented via Swagger/OpenAPI.
