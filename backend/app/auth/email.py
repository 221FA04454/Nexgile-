"""Auth email dispatch through the existing communication adapter.

Production never returns a verification URL. Local development may surface a
one-time URL so flows can be tested without a live mail provider.
"""
from __future__ import annotations

import logging

from app.core.config import get_settings

log = logging.getLogger("wealthagent.auth.email")


def dispatch_auth_email(*, purpose: str, to_email: str, subject: str, url: str, request_id: str) -> dict:
    settings = get_settings()
    from app.integrations.registry import get_provider

    provider = get_provider("email")
    result = {"delivered": False, "sandbox": True}
    if provider:
        result = provider.fetch(
            operation="send",
            payload={"to": to_email, "subject": subject, "purpose": purpose, "has_link": True},
            request_id=request_id,
            correlation_id=request_id,
        ) or result
    log.info(
        "auth_email_queued purpose=%s sandbox=%s delivered=%s request_id=%s",
        purpose,
        result.get("sandbox", True),
        result.get("delivered", False),
        request_id,
    )
    out = {
        "delivered": bool(result.get("delivered")),
        "sandbox": bool(result.get("sandbox", True)),
        "channel": "email",
    }
    if not settings.is_production:
        out["development_url"] = url
        out["development_note"] = "Development adapter only. This URL is not returned in production."
    return out
