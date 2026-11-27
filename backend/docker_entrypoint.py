"""Backend container start: wait → migrate → seed → serve."""
from __future__ import annotations

import os
import sys

os.chdir("/app")
sys.path.insert(0, "/app")

from app.core.config import get_settings, validate_settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.db.wait import wait_for_database, wait_for_redis  # noqa: E402


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=True)
    validate_settings(settings)
    if "sqlite" in settings.database_url.lower():
        raise RuntimeError("This container must use PostgreSQL. SQLite is not allowed for the Docker demo.")
    wait_for_database(settings.database_url)
    wait_for_redis(settings.redis_url)
    from alembic.config import Config
    from alembic import command

    cfg = Config("/app/alembic.ini")
    cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(cfg, "head")
    from app.db.session import SessionLocal
    from app.db.seed import seed_if_empty

    db = SessionLocal()
    try:
        seed_if_empty(db)
        db.commit()
    finally:
        db.close()
    os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])


if __name__ == "__main__":
    main()
