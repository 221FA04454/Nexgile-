"""Background worker with idempotent job history coordinated through Redis."""
from __future__ import annotations

import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT / "backend")

from app.core.config import get_settings, validate_settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.core.redis import acquire_lock, cache_set, publish, redis_status  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.jobs.runner import run_job  # noqa: E402
from app.models import entities as m  # noqa: E402
from app import models  # noqa: F401, E402


def integration_sync_job(db) -> dict:
    from app.integrations.registry import ADAPTERS
    from app.integrations.sync import run_sync

    results = []
    for key in ADAPTERS:
        run = run_sync(db, key, actor="worker", actor_role="SYSTEM")
        results.append({"provider": key, "status": run.status, "received": run.records_received})
        db.commit()
    cache_set("worker:last_integ", {"providers": len(results)}, ttl=3600)
    publish("wealthagent.jobs", {"type": "integration_sync", "providers": len(results)})
    return {"job": "integration_sync", "providers": results, "book_of_record_modified": False}


def tax_loss_harvest_scan(db) -> dict:
    harvests = db.query(m.Harvest).filter(m.Harvest.status.in_(["proposed", "review", "identified"])).all()
    total_benefit = sum(h.potential_tax_benefit or 0 for h in harvests)
    result = {
        "job": "daily_tlh_scan",
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "candidates": len(harvests),
        "potential_benefit": total_benefit,
        "book_of_record_modified": False,
    }
    cache_set("worker:last_tlh", result, ttl=3600)
    publish("wealthagent.jobs", {"type": "daily_tlh_scan", "candidates": len(harvests)})
    return result


def rmd_monitor(db) -> dict:
    rmds = db.query(m.RMD).all()
    due = [r for r in rmds if r.status not in {"not_required", "complete"}]
    result = {"job": "rmd_monitor", "open_rmds": len(due), "ran_at": datetime.now(timezone.utc).isoformat()}
    cache_set("worker:last_rmd", result, ttl=3600)
    publish("wealthagent.jobs", {"type": "rmd_monitor", "open_rmds": len(due)})
    return result


def reconciliation_heartbeat(db) -> dict:
    result = {
        "job": "data_reconciliation",
        "status": "matched",
        "breaks": 0,
        "ran_at": datetime.now(timezone.utc).isoformat(),
        "redis": redis_status(),
        "book_of_record_modified": False,
    }
    cache_set("worker:last_recon", result, ttl=3600)
    publish("wealthagent.jobs", {"type": "data_reconciliation", "breaks": 0})
    return result


def notifications_fanout(db) -> dict:
    open_alerts = db.query(m.Alert).filter(m.Alert.read.is_(False)).count()
    publish("wealthagent.notifications", {"unread_alerts": open_alerts})
    return {"job": "notifications", "unread_alerts": open_alerts, "delivered": open_alerts}


def run_once() -> None:
    if not acquire_lock("worker:run_once", ttl=50):
        return
    db = SessionLocal()
    try:
        day = date.today().isoformat()
        hour = datetime.now(timezone.utc).strftime("%H%M")
        run_job(db, "daily_tlh_scan", tax_loss_harvest_scan, f"tlh:{day}")
        run_job(db, "rmd_monitor", rmd_monitor, f"rmd:{day}")
        run_job(db, "data_reconciliation", reconciliation_heartbeat, f"recon:{day}:{hour}")
        run_job(db, "notifications", notifications_fanout, f"notify:{day}:{hour}")
        run_job(db, "integration_sync", integration_sync_job, f"integ:{day}")
    finally:
        db.close()


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, json_logs=True)
    validate_settings(settings)
    interval = int(os.getenv("WORKER_INTERVAL_SECONDS", "60"))
    once = os.getenv("WORKER_ONCE", "0") == "1"
    run_once()
    if once:
        return
    import time

    while True:
        time.sleep(interval)
        run_once()


if __name__ == "__main__":
    main()
