from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models import entities as m


def record_audit(
    db: Session,
    *,
    actor: str,
    actor_role: str = "",
    action: str,
    entity_type: str,
    entity_id: str = "",
    before: Optional[dict] = None,
    after: Optional[dict] = None,
    status: str = "recorded",
    result: str = "success",
    reason: str = "",
    request_id: str = "",
    ip_address: str = "",
) -> m.AuditEvent:
    event = m.AuditEvent(
        user=actor,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        old_value=before or {},
        new_value=after or {},
        status=status,
        result=result,
        reason=reason,
        request_id=request_id,
        ip_address=ip_address or "",
        timestamp=datetime.now(timezone.utc),
    )
    db.add(event)
    db.flush()
    return event


def lineage_payload(
    *,
    as_of: str | date = "2026-09-07",
    updated_at: Optional[datetime] = None,
    version: int = 1,
    source: str = "book_of_record",
    provider: str = "internal",
    source_record_id: str = "",
    received_at: Optional[datetime] = None,
    data_quality_status: str = "FRESH",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    updated = updated_at or now
    if updated.tzinfo is None:
        updated = updated.replace(tzinfo=timezone.utc)
    age_minutes = max(0, int((now - updated).total_seconds() / 60))
    if data_quality_status == "FRESH" and age_minutes > 60:
        data_quality_status = "STALE"
    if age_minutes <= 1:
        freshness = "Updated just now"
    elif age_minutes < 60:
        freshness = f"Updated {age_minutes} minutes ago"
    else:
        freshness = f"Updated {age_minutes // 60} hours ago"
    realtime = data_quality_status == "FRESH" and age_minutes < 15
    as_of_s = str(as_of)
    return {
        "source": source,
        "provider": provider,
        "source_record_id": source_record_id,
        "as_of": as_of_s,
        "received_at": (received_at or updated).isoformat(),
        "updated_at": updated.isoformat(),
        "freshness": freshness,
        "version": version,
        "data_quality_status": data_quality_status,
        "realtime": realtime,
        "display": {
            "as_of": f"As of {as_of_s}",
            "updated": freshness,
            "delayed": not realtime,
            "provider_unavailable": data_quality_status in {"DEGRADED", "RECONCILIATION_REQUIRED"},
            "label": "Data delayed" if not realtime else freshness,
        },
    }
