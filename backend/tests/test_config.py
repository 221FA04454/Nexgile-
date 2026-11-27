from app.core.config import Settings, validate_settings
import pytest


def test_production_rejects_sqlite():
    s = Settings.model_construct(
        environment="production",
        jwt_secret="a" * 40,
        database_url="sqlite:///./nope.db",
        redis_url="redis://localhost:6379/0",
        allow_memory_cache=False,
        allow_sqlite=False,
        allow_demo_seed=False,
        allow_create_all=False,
        cookie_secure=True,
        cors_origins="https://app.example.com",
    )
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        validate_settings(s)


def test_production_requires_jwt():
    s = Settings.model_construct(
        environment="production",
        jwt_secret="short",
        database_url="postgresql://u:p@localhost:5432/db",
        redis_url="redis://localhost:6379/0",
        allow_memory_cache=False,
        allow_sqlite=False,
        allow_demo_seed=False,
        allow_create_all=False,
        cookie_secure=True,
        cors_origins="https://app.example.com",
    )
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_settings(s)
