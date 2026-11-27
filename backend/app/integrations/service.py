"""API-facing integration operations. No credentials in any payload."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.integrations.registry import ADAPTERS, get_provider
from app.integrations.sync import run_sync
from app.models import entities as m

SECRET_KEYS = {"api_key", "secret", "password", "token", "credential", "access_token", "refresh_token"}


def _scrub(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if lk in SECRET_KEYS or lk.endswith("_secret") or lk.endswith("_password") or lk.endswith("_api_key"):
                continue
            out[k] = _scrub(v)
        return out
    if isinstance(obj, list):
        return [_scrub(v) for v in obj]
    if isinstance(obj, str) and obj.startswith("gsk_"):
        return "[redacted]"
    return obj


def _freshness(conn: m.IntegrationConnection | None) -> str:
    if not conn or not conn.last_success_at:
        return "unknown"
    return conn.freshness or "FRESH"


def list_integrations(db: Session) -> dict:
    conns = {c.provider_key: c for c in db.query(m.IntegrationConnection).all()}
    last_runs = {}
    for run in db.query(m.IntegrationSyncRun).order_by(m.IntegrationSyncRun.id.desc()).all():
        last_runs.setdefault(run.provider_key, run)
    rows = []
    for key, provider in ADAPTERS.items():
        conn = conns.get(key)
        run = last_runs.get(key)
        rows.append(
            {
                "provider": key,
                "name": provider.name,
                "category": provider.category,
                "status": conn.status if conn else provider.status,
                "live": False,
                "sandbox": True,
                "last_sync": run.finished_at.isoformat() if run and run.finished_at else None,
                "freshness": _freshness(conn),
                "records_processed": (run.records_received if run else 0),
                "created": run.created_count if run else 0,
                "updated": run.updated_count if run else 0,
                "skipped": run.skipped_count if run else 0,
                "failed": run.failed_count if run else 0,
                "error": conn.last_error if conn else "",
                "retry_status": "idle" if not run or run.status == "success" else run.status,
            }
        )
    return _scrub({"integrations": rows, "count": len(rows)})


def status_summary(db: Session) -> dict:
    data = list_integrations(db)
    recon = db.query(m.ReconciliationException).filter(m.ReconciliationException.status == "open").count()
    return _scrub(
        {
            "providers": len(data["integrations"]),
            "errors": sum(1 for r in data["integrations"] if r["status"] == "error"),
            "open_reconciliation": recon,
            "live_providers": 0,
            "sandbox": True,
        }
    )


def provider_health(db: Session, key: str) -> dict:
    provider = get_provider(key)
    if not provider:
        return None
    conn = db.query(m.IntegrationConnection).filter(m.IntegrationConnection.provider_key == key).first()
    body = provider.health()
    body.update(
        {
            "last_success_at": conn.last_success_at.isoformat() if conn and conn.last_success_at else None,
            "freshness": _freshness(conn),
            "error": conn.last_error if conn else "",
            "credentials_configured": False,
        }
    )
    return _scrub(body)


def trigger_sync(db: Session, key: str, *, actor: str, actor_role: str, request_id: str) -> dict:
    if not get_provider(key):
        return None
    run = run_sync(db, key, actor=actor, actor_role=actor_role, request_id=request_id, correlation_id=request_id)
    return _scrub(_run_payload(run))


def sync_history(db: Session, key: str) -> dict:
    rows = (
        db.query(m.IntegrationSyncRun)
        .filter(m.IntegrationSyncRun.provider_key == key)
        .order_by(m.IntegrationSyncRun.id.desc())
        .limit(25)
        .all()
    )
    return _scrub({"provider": key, "runs": [_run_payload(r) for r in rows]})


def reconciliation_queue(db: Session) -> dict:
    rows = (
        db.query(m.ReconciliationException)
        .order_by(m.ReconciliationException.id.desc())
        .limit(100)
        .all()
    )
    return _scrub(
        {
            "exceptions": [
                {
                    "id": r.id,
                    "provider": r.provider_key,
                    "type": r.exception_type,
                    "entity_type": r.entity_type,
                    "household_id": r.household_id,
                    "external_id": r.external_id,
                    "detail": r.detail,
                    "status": r.status,
                    "severity": r.severity,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
        }
    )


def _run_payload(run: m.IntegrationSyncRun) -> dict:
    return {
        "id": run.id,
        "provider": run.provider_key,
        "entity_type": run.entity_type,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "records_received": run.records_received,
        "created": run.created_count,
        "updated": run.updated_count,
        "skipped": run.skipped_count,
        "failed": run.failed_count,
        "status": run.status,
        "error": run.error,
        "request_id": run.request_id,
        "correlation_id": run.correlation_id,
    }
