"""Optional Google OIDC sign-in and role checks for METEORWATCH.

Public dashboard access does not depend on authentication. This module only
identifies approved team/admin accounts for future restricted features.
It deliberately keeps authorisation decisions separate from identity login.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

GOOGLE_OIDC_METADATA_URL = "https://accounts.google.com/.well-known/openid-configuration"
ROLE_LEVELS = {"public": 0, "team_member": 1, "admin": 2}


def _get(value: Any, key: str, default: Any = None) -> Any:
    """Read a key from dict-like Streamlit secrets/user objects or plain mappings."""
    if isinstance(value, Mapping):
        return value.get(key, default)
    getter = getattr(value, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except Exception:
            pass
    return getattr(value, key, default)


def _section(secrets: Any, name: str) -> Any:
    try:
        return _get(secrets, name, {})
    except Exception:
        return {}


def _configured_value(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    cleaned = value.strip()
    if not cleaned:
        return False
    upper = cleaned.upper()
    return not (
        upper.startswith("REPLACE_")
        or upper.startswith("YOUR_")
        or "PASTE_" in upper
    )


def _email_set(value: Any) -> frozenset[str]:
    """Normalise an email allowlist supplied as a TOML list or comma-separated string."""
    if isinstance(value, str):
        values = value.replace(";", ",").split(",")
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = value
    else:
        values = ()

    emails = set()
    for item in values:
        if not isinstance(item, str):
            continue
        email = item.strip().casefold()
        if email and "@" in email and not email.startswith("@") and not email.endswith("@"):
            emails.add(email)
    return frozenset(emails)


def read_auth_settings(secrets: Any) -> dict[str, Any]:
    """Read Google OIDC settings and private role allowlists from Streamlit secrets.

    The application stays public when these secrets are absent or incomplete.
    """
    auth = _section(secrets, "auth")
    access = _section(secrets, "access")

    metadata_url = _get(auth, "server_metadata_url", "")
    required = (
        _get(auth, "redirect_uri", ""),
        _get(auth, "cookie_secret", ""),
        _get(auth, "client_id", ""),
        _get(auth, "client_secret", ""),
    )
    auth_configured = (
        all(_configured_value(value) for value in required)
        and metadata_url == GOOGLE_OIDC_METADATA_URL
    )

    return {
        "auth_configured": bool(auth_configured),
        "team_emails": _email_set(_get(access, "team_emails", ())),
        "admin_emails": _email_set(_get(access, "admin_emails", ())),
    }


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().casefold() in {"true", "1", "yes"}
    return False


def get_access_context(user: Any, settings: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve the current signed-in identity to public, team_member, or admin.

    Google email must be explicitly verified and present in the relevant
    private allowlist. Admins automatically inherit team-member permissions.
    """
    is_logged_in = _as_bool(_get(user, "is_logged_in", False))
    email_value = _get(user, "email", "")
    email = email_value.strip().casefold() if isinstance(email_value, str) else ""
    email_verified = _as_bool(_get(user, "email_verified", False))
    auth_configured = bool(settings.get("auth_configured", False))

    admins = settings.get("admin_emails", frozenset())
    members = settings.get("team_emails", frozenset())
    admins = admins if isinstance(admins, (set, frozenset, list, tuple)) else ()
    members = members if isinstance(members, (set, frozenset, list, tuple)) else ()

    role = "public"
    if auth_configured and is_logged_in and email and email_verified:
        admin_set = {str(item).strip().casefold() for item in admins}
        member_set = {str(item).strip().casefold() for item in members}
        if email in admin_set:
            role = "admin"
        elif email in member_set:
            role = "team_member"

    return {
        "auth_configured": auth_configured,
        "is_logged_in": is_logged_in,
        "email": email or None,
        "email_verified": email_verified,
        "role": role,
        "is_team_member": role in {"team_member", "admin"},
        "is_admin": role == "admin",
    }


def role_allows(context: Mapping[str, Any], required_role: str) -> bool:
    """Return whether the resolved role meets a minimum role requirement."""
    if required_role not in ROLE_LEVELS:
        raise ValueError(f"Unknown role: {required_role}")
    role = context.get("role", "public")
    if role not in ROLE_LEVELS:
        role = "public"
    return ROLE_LEVELS[role] >= ROLE_LEVELS[required_role]
