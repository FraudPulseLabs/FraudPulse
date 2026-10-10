#!/usr/bin/env bash
#
# Keep the Supabase project from auto-pausing.
#
# The free tier pauses a project after ~7 days without activity. This makes one
# cheap request through Supabase's API gateway, which counts as activity, and
# then checks that the backend can reach Postgres itself.
#
# Intended for cron on the OCI VM, which already runs 24/7 — no third-party
# service and nothing to sign up for.
#
# Configuration comes from the environment, or from an env file passed as the
# first argument / via KEEPALIVE_ENV_FILE:
#
#   SUPABASE_URL                 https://<project-ref>.supabase.co
#   SUPABASE_SERVICE_ROLE_KEY    service-role key (bypasses RLS — keep private)
#   HEALTH_URL                   optional; defaults to the public backend
#
# Install (run as the user that owns the deploy, not root):
#
#   chmod +x /opt/fraudpulse/keepalive.sh
#   crontab -e
#   17 6 */2 * * /opt/fraudpulse/keepalive.sh /opt/fraudpulse/.env >> /var/log/fraudpulse-keepalive.log 2>&1
#
# Verify with:  ./keepalive.sh /path/to/.env && echo OK

set -euo pipefail

ENV_FILE="${1:-${KEEPALIVE_ENV_FILE:-}}"
if [ -n "${ENV_FILE}" ]; then
  if [ ! -r "${ENV_FILE}" ]; then
    echo "$(date -Is) ERROR env file not readable: ${ENV_FILE}" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  set -a; . "${ENV_FILE}"; set +a
fi

: "${SUPABASE_URL:?SUPABASE_URL is not set}"
: "${SUPABASE_SERVICE_ROLE_KEY:?SUPABASE_SERVICE_ROLE_KEY is not set}"
HEALTH_URL="${HEALTH_URL:-https://fraudpulse.duckdns.org/health/db}"

log() { echo "$(date -Is) $*"; }

# 1. Request through the Supabase API gateway. Cheapest query that still
#    touches Postgres: one column, one row.
code=$(curl -sS --max-time 30 -o /tmp/fraudpulse-keepalive-body -w '%{http_code}' \
  "${SUPABASE_URL}/rest/v1/transactions?select=id&limit=1" \
  -H "apikey: ${SUPABASE_SERVICE_ROLE_KEY}" \
  -H "Authorization: Bearer ${SUPABASE_SERVICE_ROLE_KEY}" || echo "000")

if [ "${code}" != "200" ]; then
  log "ERROR PostgREST returned HTTP ${code}"
  # Never log the body unfiltered on failure — Supabase errors can echo
  # connection details. Truncate to something diagnostic but harmless.
  head -c 200 /tmp/fraudpulse-keepalive-body >&2; echo >&2
  exit 1
fi
log "OK PostgREST HTTP 200"

# 2. Confirm the backend itself can still reach Postgres. Non-fatal: the
#    keep-alive above already succeeded, and we do not want cron spamming
#    failures because the API is mid-redeploy.
if body=$(curl -fsS --max-time 30 "${HEALTH_URL}" 2>/dev/null) \
   && printf '%s' "${body}" | grep -q '"database":"ok"'; then
  log "OK backend readiness"
else
  log "WARN backend readiness check failed (Supabase itself is awake)"
fi
