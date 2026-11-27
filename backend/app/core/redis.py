"""Redis cache, rate limiting, and pub/sub with explicit development fallback."""
from __future__ import annotations

from typing import Any, Optional
import json
import logging
import time

from app.core.config import get_settings
from app.core.errors import AppError

log = logging.getLogger("wealthagent.redis")

_memory_store: dict[str, tuple[Any, Optional[float]]] = {}
_client = None
_init = False


def get_redis(required: bool = False):
    global _client, _init
    settings = get_settings()
    if _init:
        if _client is None and (required or settings.is_production or not settings.allow_memory_cache):
            raise AppError("SERVICE_UNAVAILABLE", "Redis is unavailable.", 503)
        return _client
    _init = True
    if not settings.redis_url:
        if settings.is_production or not settings.allow_memory_cache:
            raise AppError("SERVICE_UNAVAILABLE", "REDIS_URL is not configured.", 503)
        log.warning("redis_disabled_memory_fallback")
        return None
    try:
        import redis

        client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=settings.redis_socket_timeout,
            socket_timeout=settings.redis_socket_timeout,
            retry_on_timeout=True,
            health_check_interval=15,
        )
        client.ping()
        _client = client
        return client
    except Exception as exc:
        log.error("redis_connect_failed err=%s", type(exc).__name__)
        if settings.is_production or not settings.allow_memory_cache:
            _client = None
            if required:
                raise AppError("SERVICE_UNAVAILABLE", "Redis is unavailable.", 503) from exc
            raise
        log.warning("redis_memory_fallback_enabled")
        _client = None
        return None


def reset_redis_client() -> None:
    global _client, _init
    _client = None
    _init = False
    _memory_store.clear()


def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    payload = json.dumps(value, default=str)
    client = get_redis()
    if client is not None:
        client.setex(key, ttl, payload)
        return
    expires = time.time() + ttl if ttl else None
    _memory_store[key] = (payload, expires)


def cache_get(key: str) -> Optional[Any]:
    client = get_redis()
    if client is not None:
        raw = client.get(key)
        return json.loads(raw) if raw else None
    item = _memory_store.get(key)
    if not item:
        return None
    payload, expires = item
    if expires and time.time() > expires:
        _memory_store.pop(key, None)
        return None
    return json.loads(payload)


def cache_delete(key: str) -> None:
    client = get_redis()
    if client is not None:
        client.delete(key)
        return
    _memory_store.pop(key, None)


def cache_delete_prefix(prefix: str) -> None:
    client = get_redis()
    if client is not None:
        for key in client.scan_iter(match=f"{prefix}*"):
            client.delete(key)
        return
    for key in list(_memory_store):
        if key.startswith(prefix):
            _memory_store.pop(key, None)


def incr_with_ttl(key: str, ttl: int) -> int:
    client = get_redis()
    if client is not None:
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, ttl, nx=True)
        count, _ = pipe.execute()
        return int(count)
    now = time.time()
    item = _memory_store.get(key)
    if not item or (item[1] and now > item[1]):
        _memory_store[key] = (json.dumps(1), now + ttl)
        return 1
    count = int(json.loads(item[0])) + 1
    _memory_store[key] = (json.dumps(count), item[1])
    return count


def publish(channel: str, message: dict) -> None:
    client = get_redis()
    if client is None:
        return
    client.publish(channel, json.dumps(message, default=str))


def acquire_lock(key: str, ttl: int = 120) -> bool:
    client = get_redis()
    if client is None:
        return True
    return bool(client.set(f"lock:{key}", "1", nx=True, ex=ttl))


def release_lock(key: str) -> None:
    client = get_redis()
    if client is None:
        return
    client.delete(f"lock:{key}")


def redis_status() -> dict:
    try:
        client = get_redis()
    except AppError:
        return {"status": "unavailable", "available": False, "backend": "unavailable", "required": True}
    if client is None:
        return {"status": "memory_fallback", "available": False, "backend": "memory_fallback", "required": False}
    try:
        client.ping()
        return {"status": "healthy", "available": True, "backend": "redis", "required": True}
    except Exception:
        return {"status": "unavailable", "available": False, "backend": "error", "required": True}


def redis_ready() -> bool:
    status = redis_status()
    if status["backend"] == "memory_fallback" and get_settings().allow_memory_cache:
        return True
    return bool(status.get("available"))
