"""Integration provider contract. Business code talks to this interface only."""
from __future__ import annotations

import time
import uuid
from typing import Any, Protocol

RETRYABLE_CODES = {"timeout", "unavailable", "rate_limit", "http_5xx"}
PERMANENT_CODES = {"invalid_credentials", "unauthorized", "invalid_request", "malformed"}


class ProviderError(Exception):
    def __init__(self, code: str, message: str = "Provider unavailable", retryable: bool | None = None):
        self.code = code
        self.message = message
        self.retryable = RETRYABLE_CODES.__contains__(code) if retryable is None else retryable
        super().__init__(message)


class IntegrationProvider(Protocol):
    key: str
    name: str
    category: str
    timeout_seconds: float

    def health(self) -> dict: ...
    def fetch(self, *, operation: str, payload: dict, request_id: str, correlation_id: str, db=None) -> dict: ...


class BaseMockProvider:
    """Deterministic sandbox adapter. Never holds credentials. Never calls live APIs."""

    timeout_seconds = 8.0
    max_retries = 3
    live = False
    status = "mock"

    def __init__(self, key: str, name: str, category: str):
        self.key = key
        self.name = name
        self.category = category

    def health(self) -> dict:
        return {
            "provider": self.key,
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "live": False,
            "sandbox": True,
        }

    def execute(self, operation: str, payload: dict | None = None, db=None, request_id: str = "", correlation_id: str = "") -> dict:
        request_id = request_id or str(uuid.uuid4())
        correlation_id = correlation_id or request_id
        last_error: ProviderError | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                data = self.fetch(
                    operation=operation,
                    payload=payload or {},
                    request_id=request_id,
                    correlation_id=correlation_id,
                    db=db,
                )
                return {
                    "ok": True,
                    "provider": self.key,
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "attempt": attempt,
                    "data": data,
                    "live": False,
                }
            except ProviderError as exc:
                last_error = exc
                if not exc.retryable or attempt == self.max_retries:
                    break
                time.sleep(min(2.0, 0.05 * (2 ** attempt)))
        return {
            "ok": False,
            "provider": self.key,
            "request_id": request_id,
            "correlation_id": correlation_id,
            "error": last_error.code if last_error else "unavailable",
            "message": "Integration provider is temporarily unavailable." if (last_error and last_error.retryable) else "Integration request could not be completed.",
            "live": False,
        }

    def fetch(self, *, operation: str, payload: dict, request_id: str, correlation_id: str, db=None) -> dict:
        return {
            "adapter": self.key,
            "operation": operation,
            "sandbox": True,
            "delivered": False,
            "executed": False,
            "book_of_record_modified": False,
        }
