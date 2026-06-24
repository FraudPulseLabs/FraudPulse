# Frequently Asked Questions

## What does FraudPulse do?

FraudPulse is a real-time fraud detection platform for card and account
payments. It scores each transaction for fraud risk and routes it to ALLOW,
REVIEW, or BLOCK, helping stop fraud before it settles while keeping friction
low for legitimate customers.

## How fast is scoring?

Scoring happens in real time, within milliseconds, so it can run inline during
payment authorization without adding noticeable latency.

## Does FraudPulse use machine learning or rules?

Both. FraudPulse runs a deterministic rule engine alongside a calibrated
LightGBM machine-learning model. Rules capture known, explainable patterns and
the model catches subtler anomalies; their results are combined into the final
decision.

## What are the possible decisions?

There are three: ALLOW (cleared), REVIEW (held for an analyst), and BLOCK
(declined as high risk). REVIEW and BLOCK outcomes create alerts and cases.

## Can I see why a transaction was flagged?

Yes. Every score stores its top contributing features and any rules that fired.
Analysts can see this explanation in the dashboard, and it is kept in the audit
trail.

## What is the difference between an alert and a case?

An alert is a single thing that needs attention, created when a transaction is
sent to REVIEW or BLOCK. A case is the unit of investigation an analyst works;
related alerts are grouped into a case with a lifecycle from open to closed.

## How do I integrate FraudPulse?

Integrate through the REST API under ``/api/v1``. Send transactions to the
scoring endpoint and act on the returned decision. Protected endpoints require
a Supabase-issued JWT. See the API Reference for details.

## Is there a way to try it without signing up?

Yes. The public model demo lets you score sample transactions through the live
model without an account and without storing any data.

## How is FraudPulse hosted?

The FastAPI backend runs as a Docker container on Oracle Cloud Infrastructure.
The Angular dashboard is hosted on Render. Data lives in Postgres via Supabase.

## How much does FraudPulse cost?

Pricing is not listed publicly and depends on volume and use case. Submit the
Request access form for details tailored to your needs.

## How do I contact the team?

Use the Request access form on the landing page. The team responds within one
business day.

## What powers the landing-page assistant?

The assistant uses a retrieval-augmented-generation (RAG) pipeline. It
retrieves relevant passages from FraudPulse's documentation and uses a Groq
large language model to generate a grounded, cited answer. It only answers from
the documentation and will say so when a question is out of scope.
