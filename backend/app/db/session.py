from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

Base = declarative_base()

_engine = None
_SessionLocal = None


def _create_engine(settings):
    url = settings.database_url
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    if url.startswith("sqlite"):
        if not settings.allow_sqlite:
            raise RuntimeError("SQLite is not permitted unless ALLOW_SQLITE=true")
        from sqlalchemy.pool import StaticPool

        kwargs = {"connect_args": {"check_same_thread": False}, "future": True}
        if ":memory:" in url or url.endswith("sqlite://"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    return create_engine(
        url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
        future=True,
    )


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = _create_engine(settings)
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine, future=True)
    return _engine


def get_session_factory():
    get_engine()
    return _SessionLocal


def reset_engine() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


# Lazy alias used by existing imports
class _EngineProxy:
    def __getattr__(self, item):
        return getattr(get_engine(), item)

    def __call__(self, *args, **kwargs):
        return get_engine()(*args, **kwargs)


engine = _EngineProxy()


class _SessionProxy:
    def __call__(self, *args, **kwargs):
        return get_session_factory()(*args, **kwargs)


SessionLocal = _SessionProxy()


def get_db():
    db = get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def database_backend_name(url: str | None = None) -> str:
    url = (url or get_settings().database_url or "").lower()
    if url.startswith("postgres"):
        return "postgresql"
    if url.startswith("sqlite"):
        return "sqlite"
    return "unknown"


def database_status() -> dict:
    backend = database_backend_name()
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "backend": backend, "available": True}
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "unavailable",
            "backend": backend,
            "available": False,
            "error": type(exc).__name__,
        }


def database_ready() -> bool:
    return bool(database_status().get("available"))
