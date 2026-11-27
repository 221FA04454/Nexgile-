from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    app_name: str = "Nexgile WealthAgent"
    app_version: str = "0.2.0"
    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    jwt_secret: str = Field(default="", validation_alias=AliasChoices("JWT_SECRET", "SECRET_KEY"))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    database_url: str = Field(default="", validation_alias=AliasChoices("DATABASE_URL"))
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    redis_url: str = Field(default="", validation_alias=AliasChoices("REDIS_URL"))
    redis_socket_timeout: float = 2.0
    allow_memory_cache: bool = False
    allow_sqlite: bool = False
    allow_demo_seed: bool = True
    allow_create_all: bool = True

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    as_of_date: str = "2026-09-07"
    data_provider: str = "internal_book_of_record"
    upload_dir: str = "../uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    groq_api_key: str = ""
    groq_api_base: str = "https://api.groq.com/openai/v1"
    groq_model: str = "openai/gpt-oss-120b"
    groq_timeout_seconds: float = 20.0
    groq_retries: int = 2
    ai_provider: str = "deterministic"
    ai_allow_deterministic_fallback: bool = True
    ai_prompt_version: str = "wa-prompt-v1"
    embedding_backend: str = "hashed"
    embedding_dim: int = 256
    cookie_secure: bool = False
    login_rate_limit: int = 8
    login_rate_window_seconds: int = 60
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    public_app_url: str = Field(default="http://localhost:5173", validation_alias=AliasChoices("PUBLIC_APP_URL"))
    verification_token_minutes: int = 60
    reset_token_minutes: int = 30
    auth_email_rate_limit: int = 5
    auth_email_rate_window_seconds: int = 300
    signup_rate_limit: int = 8
    signup_rate_window_seconds: int = 60
    object_storage_backend: str = "local"
    s3_bucket: str = ""
    s3_endpoint: str = ""
    s3_region: str = "us-east-1"
    default_currency: str = "INR"
    default_currency_symbol: str = "₹"
    default_locale: str = "en-IN"

    @field_validator("environment", mode="before")
    @classmethod
    def _norm_env(cls, v):
        if v is None:
            return "development"
        return str(v).lower()

    @property
    def cors_origin_list(self):
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"

    @property
    def demo_login_enabled(self) -> bool:
        return self.allow_demo_seed and not self.is_production


def validate_settings(settings: Settings) -> None:
    missing = []
    if not settings.jwt_secret or len(settings.jwt_secret) < 32:
        missing.append("JWT_SECRET (min 32 characters)")
    if not settings.database_url:
        missing.append("DATABASE_URL")
    if settings.is_production:
        if "sqlite" in settings.database_url.lower():
            raise RuntimeError("PostgreSQL is required in production. SQLite is not a production database.")
        if not settings.database_url.lower().startswith("postgres"):
            raise RuntimeError("DATABASE_URL must be a PostgreSQL URL in production.")
        if settings.jwt_secret.startswith("nexgile-wealthagent-mvp") or "change-in-production" in settings.jwt_secret:
            raise RuntimeError("JWT_SECRET must not use the MVP default in production.")
        if not settings.redis_url:
            missing.append("REDIS_URL")
        if settings.allow_memory_cache:
            raise RuntimeError("ALLOW_MEMORY_CACHE cannot be enabled in production.")
        if settings.allow_sqlite:
            raise RuntimeError("ALLOW_SQLITE cannot be enabled in production.")
        if settings.allow_demo_seed:
            raise RuntimeError("ALLOW_DEMO_SEED cannot be enabled in production.")
        if settings.allow_create_all:
            raise RuntimeError("ALLOW_CREATE_ALL cannot be enabled in production. Use Alembic migrations.")
        if not settings.cookie_secure:
            raise RuntimeError("COOKIE_SECURE must be true in production.")
        if not settings.cors_origin_list:
            raise RuntimeError("CORS_ORIGINS must be an explicit allow-list in production.")
    else:
        if "sqlite" in settings.database_url.lower() and not settings.allow_sqlite:
            raise RuntimeError("SQLite is disabled unless ALLOW_SQLITE=true (development/test only).")
        if not settings.redis_url and not settings.allow_memory_cache:
            missing.append("REDIS_URL (or set ALLOW_MEMORY_CACHE=true for development/test)")
    if missing:
        raise RuntimeError("Missing required configuration: " + ", ".join(missing))


@lru_cache
def get_settings() -> Settings:
    return Settings()
