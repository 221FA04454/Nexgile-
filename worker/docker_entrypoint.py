"""Worker container start: wait for Postgres + Redis, then run jobs."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path("/workspace")
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

from app.core.config import get_settings, validate_settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.db.wait import wait_for_database, wait_for_redis  # noqa: E402


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=True)
    validate_settings(settings)
    if "sqlite" in settings.database_url.lower():
        raise RuntimeError("Worker must use PostgreSQL.")
    wait_for_database(settings.database_url)
    wait_for_redis(settings.redis_url)
    os.execvp("python", ["python", "/workspace/worker/main.py"])


if __name__ == "__main__":
    main()
