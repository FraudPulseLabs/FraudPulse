"""Supabase Auth Admin API client (service-role).

The backend normally only *verifies* Supabase-issued JWTs (see
[src/core/auth.py]). Approving an access request, however, requires
*provisioning* a user in Supabase Auth — a privileged operation that hits the
GoTrue admin API (``/auth/v1/admin/users``) with the project's service-role key.

That key must never reach the browser; it lives only in the backend
environment (``SUPABASE_SERVICE_ROLE_KEY``).
"""

from __future__ import annotations

import httpx

from src.core import config


class SupabaseConfigError(RuntimeError):
    """Supabase admin calls are not configured (URL or service-role key missing)."""


class SupabaseAdminError(RuntimeError):
    """The Supabase admin API returned an unexpected (non-2xx) response."""


class UserAlreadyExists(RuntimeError):
    """The email is already registered in Supabase Auth."""


_TIMEOUT = httpx.Timeout(10.0)


def _admin_headers() -> dict[str, str]:
    key = config.SUPABASE_SERVICE_ROLE_KEY
    if not config.SUPABASE_URL or not key:
        raise SupabaseConfigError(
            "Supabase provisioning is not configured. Set SUPABASE_SERVICE_ROLE_KEY "
            "(and SUPABASE_URL) in backend/.env to approve access requests."
        )
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _error_detail(resp: httpx.Response) -> str:
    try:
        data = resp.json()
    except Exception:
        return resp.text or "unknown error"
    if isinstance(data, dict):
        return str(
            data.get("msg")
            or data.get("message")
            or data.get("error_description")
            or data.get("error")
            or data
        )
    return str(data)


async def create_auth_user(email: str, password: str) -> dict:
    """Create a pre-confirmed email/password user in Supabase Auth.

    ``email_confirm=True`` means the user can sign in immediately without an
    email round-trip.

    Raises:
        SupabaseConfigError: when the URL / service-role key are not set.
        UserAlreadyExists:   when the email already has an account.
        SupabaseAdminError:  on any other non-2xx response.
    """
    headers = _admin_headers()
    url = f"{config.SUPABASE_URL}/auth/v1/admin/users"
    body = {"email": email, "password": password, "email_confirm": True}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=body, headers=headers)

    if resp.status_code in (200, 201):
        return resp.json()

    # GoTrue reports a duplicate email with 422 and an "already registered" /
    # "email_exists" message — surface that as a distinct, recoverable error.
    detail = _error_detail(resp)
    lowered = detail.lower()
    if resp.status_code in (409, 422) and ("already" in lowered or "exists" in lowered):
        raise UserAlreadyExists(email)
    raise SupabaseAdminError(f"{resp.status_code}: {detail}")
