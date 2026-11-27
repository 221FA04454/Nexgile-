from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.core.config import get_settings, validate_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.redis import redis_ready, reset_redis_client
from app.db.seed import seed_if_empty
from app.db.session import Base, SessionLocal, database_ready, get_engine
from app import models  # noqa: F401

settings = get_settings()
configure_logging(settings.log_level, json_logs=True)
log = logging.getLogger("wealthagent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings(settings)
    reset_redis_client()
    if settings.allow_create_all:
        Base.metadata.create_all(bind=get_engine())
    if settings.allow_demo_seed:
        db = SessionLocal()
        try:
            seed_if_empty(db)
            db.commit()
        finally:
            db.close()
    log.info("startup environment=%s", settings.environment)
    yield


app = FastAPI(
    title="Nexgile WealthAgent API",
    description="AI-powered wealth management portal",
    version=settings.app_version,
    docs_url=None if settings.is_production else "/api/docs",
    redoc_url=None if settings.is_production else "/api/redoc",
    openapi_url=None if settings.is_production else "/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID", "Idempotency-Key", "X-Refresh-Token"],
)

register_exception_handlers(app, settings)
app.include_router(router, prefix="/api")


@app.get("/")
def root():
    return {"name": settings.app_name, "health": "/api/health"}
