"""Backward-compatible adapter catalog."""
from app.integrations.base import BaseMockProvider as IntegrationAdapter
from app.integrations.base import BaseMockProvider as MockAdapter
from app.integrations.base import ProviderError
from app.integrations.registry import ADAPTERS, catalog, get_provider

__all__ = ["ADAPTERS", "catalog", "get_provider", "IntegrationAdapter", "MockAdapter", "ProviderError"]
