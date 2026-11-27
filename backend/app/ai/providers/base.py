from __future__ import annotations

from typing import Protocol

USER_UNAVAILABLE = "AI service is temporarily unavailable. Please try again."


class ProviderError(Exception):
    """Provider failure that is safe to log by code, never by secret."""

    def __init__(self, code: str, user_message: str = USER_UNAVAILABLE):
        self.code = code
        self.user_message = user_message
        super().__init__(code)


class AIProvider(Protocol):
    name: str
    model: str

    def generate(self, *, system_prompt: str, user_message: str, context: dict, documents: list[dict]) -> dict:
        """Return answer, token_usage, model. Must not mutate books of record."""
