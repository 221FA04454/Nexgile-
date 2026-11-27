"""Validate relational demo data. Exit non-zero on orphaned or missing core records.

Usage from repo root (DATABASE_URL must point at the running database):

    python scripts/validate_demo_data.py

Inside Docker:

    docker compose exec backend python -m app.db.validate_demo
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from app.db.validate_demo import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
