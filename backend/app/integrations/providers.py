"""Mock integration providers. No live APIs, no credentials, no real trades or messages."""
from __future__ import annotations

from app.integrations.base import BaseMockProvider, ProviderError
from app.integrations import feeds


class FinancialProvider(BaseMockProvider):
    category = "financial"

    def fetch(self, *, operation: str, payload: dict, request_id: str, correlation_id: str, db=None) -> dict:
        if operation in {"place_order", "execute", "execute_trade"}:
            return {
                "orders": [{"status": "sandbox_rejected", "executed": False, "book_of_record_modified": False}],
                "note": "Broker OMS is mock/sandbox only. No live trade is sent.",
            }
        if db is None:
            return {"accounts": [], "holdings": [], "sandbox": True}
        snap = feeds.financial_snapshot(db)
        if self.key == "market_pricing":
            return {"prices": snap["prices"], "security_metadata": snap["holdings"]}
        if self.key == "alternatives":
            return {"valuations": snap["alternatives"] or snap["accounts"][:1]}
        if self.key == "broker_dealer":
            snap["orders"] = [{"status": "sandbox", "executed": False, "book_of_record_modified": False}]
        return snap


class BusinessProvider(BaseMockProvider):
    category = "business"

    def fetch(self, *, operation: str, payload: dict, request_id: str, correlation_id: str, db=None) -> dict:
        if db is None:
            return {"clients": [], "sandbox": True}
        return feeds.business_snapshot(db)


class RetirementProvider(BaseMockProvider):
    category = "retirement"

    def fetch(self, *, operation: str, payload: dict, request_id: str, correlation_id: str, db=None) -> dict:
        if db is None:
            return {"participants": [], "sandbox": True}
        return feeds.retirement_snapshot(db)


class CommunicationProvider(BaseMockProvider):
    category = "communication"

    def fetch(self, *, operation: str, payload: dict, request_id: str, correlation_id: str, db=None) -> dict:
        return {
            "channel": self.key,
            "delivered": False,
            "sandbox": True,
            "note": "Local demo does not send email, SMS, push, calendar, or video.",
        }


class IdentityProvider(BaseMockProvider):
    category = "identity"

    def fetch(self, *, operation: str, payload: dict, request_id: str, correlation_id: str, db=None) -> dict:
        return {
            "sso_enabled": False,
            "authority": "local_jwt",
            "note": "Existing authentication is unchanged. SSO is not enabled in the local demo.",
        }


class DocumentProvider(BaseMockProvider):
    category = "documents"

    def fetch(self, *, operation: str, payload: dict, request_id: str, correlation_id: str, db=None) -> dict:
        return {
            "sent": False,
            "signed": False,
            "archived": False,
            "sandbox": True,
            "note": "E-signature and compliance archive are mock only.",
        }


class FlakyProvider(BaseMockProvider):
    """Used in tests to exercise retry. Production registry does not include this key."""

    def __init__(self):
        super().__init__("flaky", "Flaky Test Feed", "financial")
        self.failures_remaining = 1

    def fetch(self, *, operation: str, payload: dict, request_id: str, correlation_id: str, db=None) -> dict:
        if self.failures_remaining > 0:
            self.failures_remaining -= 1
            raise ProviderError("unavailable", retryable=True)
        return {"ok": True, "recovered": True}


class PermanentFailProvider(BaseMockProvider):
    def __init__(self):
        super().__init__("permfail", "Permanent Fail", "financial")

    def fetch(self, *, operation: str, payload: dict, request_id: str, correlation_id: str, db=None) -> dict:
        raise ProviderError("invalid_credentials", retryable=False)
