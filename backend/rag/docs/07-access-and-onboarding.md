# Access and Onboarding

## How to get access to FraudPulse

FraudPulse is available through **early access**. To request access:

1. Visit the landing page: `https://fraudpulse-u2va.onrender.com/`
2. Use the **Request access** form
3. Submit your work email and optionally your company name
4. The team typically follows up within **one business day**

There is no self-serve public signup. Access is provisioned by the FraudPulse
team so each deployment can be configured for the customer's portfolio.

## Signing in to the dashboard

Once your account is provisioned:

1. Go to the FraudPulse site and click **Sign In**
2. Authenticate through **Supabase Auth**
3. You land in the analyst dashboard (default route: **Overview**)

Dashboard sections: Overview, Transactions, Alerts, Cases, Watchlist, and Model
Demo.

## Trying the model demo without an account

You do **not** need an account to try scoring:

- Use the **model demo** on the landing page
- Or call the public demo API: `POST /api/v1/demo/score`
- Demo scoring uses sample data and does **not** persist to the database

This is a good way to see ALLOW / REVIEW / BLOCK outcomes before full onboarding.

## Using the landing-page assistant

The public **chatbot widget** answers common questions about FraudPulse —
scoring, decisions, the API, architecture, security, and onboarding. It draws
answers only from the product documentation.

## Onboarding steps for new customers

A typical onboarding path:

1. Submit the Request access form and introductory call
2. Receive provisioned dashboard accounts for analysts
3. Integrate `POST /api/v1/transactions` into your authorization flow
4. Tune decision thresholds and rules with the FraudPulse team
5. Train analysts on alerts, cases, and watchlists in the dashboard

## API documentation for integrators

Interactive API docs are available at:

- Local: `http://localhost:8000/docs`
- Production: `https://fraudpulse.duckdns.org/docs`

## Pricing

Pricing is **not published** on the public site. It depends on transaction
volume and use case. Submit the Request access form for tailored pricing.

## Getting help

- **Product questions:** use the landing-page assistant or Request access form
- **Access requests:** Request access form (response within one business day)
- **API health:** `GET https://fraudpulse.duckdns.org/health`
