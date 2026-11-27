import logging

from app.ai.providers.deterministic import DeterministicProvider
from app.ai.providers.groq import GroqProvider
from app.core.config import get_settings

log = logging.getLogger("wealthagent.ai.providers")


def resolve_provider():
    settings = get_settings()
    requested = (settings.ai_provider or "deterministic").lower()
    if requested == "groq":
        if settings.groq_api_key:
            return GroqProvider()
        log.warning("groq_unavailable_using_deterministic")
        return DeterministicProvider()
    return DeterministicProvider()
