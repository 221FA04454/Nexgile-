"""Wait for PostgreSQL (and optionally Redis) before serving traffic."""
from __future__ import annotations

import os
import time
import logging

log = logging.getLogger("wealthagent.boot")


def wait_for_database(url: str | None = None, attempts: int = 60, delay: float = 1.0) -> None:
    from sqlalchemy import create_engine, text

    url = url or os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    if url.startswith("sqlite"):
        return
    last = None
    for i in range(attempts):
        try:
            engine = create_engine(url, pool_pre_ping=True, future=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            engine.dispose()
            log.info("postgres_ready attempt=%s", i + 1)
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            log.warning("postgres_wait attempt=%s err=%s", i + 1, type(exc).__name__)
            time.sleep(delay)
    raise RuntimeError(f"PostgreSQL is unavailable after {attempts} attempts: {type(last).__name__}")


def wait_for_redis(url: str | None = None, attempts: int = 30, delay: float = 1.0) -> None:
    url = url or os.environ.get("REDIS_URL", "")
    if not url:
        raise RuntimeError("REDIS_URL is not configured")
    import redis

    last = None
    for i in range(attempts):
        try:
            client = redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
            client.ping()
            log.info("redis_ready attempt=%s", i + 1)
            return
        except Exception as extra:  # noqa: BLE001
            last = extra
            log.warning("redis_wait attempt=%s err=%s", i + 1, type(extra).__name__)
            time.sleep(delay)
    raise RuntimeError(f"Redis is unavailable after {attempts} attempts: {type(last).__name__}")
