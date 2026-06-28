-- Access request waitlist for enterprise onboarding.
-- Run against the Supabase/Postgres public schema.

CREATE TABLE IF NOT EXISTS access_requests (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT NOT NULL,
    company     TEXT,
    source_ip   TEXT,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS access_requests_email_unique
    ON access_requests (lower(email));

CREATE INDEX IF NOT EXISTS access_requests_created_at_idx
    ON access_requests (created_at DESC);
