"""Fetch → validate → normalize → dedupe → lineage. Never duplicates books of record."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import utcnow
from app.integrations.feeds import ORPHAN_EXTERNAL_ID
from app.integrations.reconcile import reconcile_financial
from app.integrations.registry import get_provider
from app.models import entities as m
from app.services.audit import record_audit

log = logging.getLogger("wealthagent.integrations")


def _now():
    return datetime.now(timezone.utc)


def _link(db: Session, provider: str, entity_type: str, external_id: str, internal_id: int | None, household_id: int | None, run_id: int) -> str:
    row = (
        db.query(m.IntegrationRecordLink)
        .filter(
            m.IntegrationRecordLink.provider_key == provider,
            m.IntegrationRecordLink.entity_type == entity_type,
            m.IntegrationRecordLink.external_id == external_id,
        )
        .first()
    )
    if row:
        row.last_sync_run_id = run_id
        row.internal_id = internal_id if internal_id is not None else row.internal_id
        row.updated_at = _now()
        return "updated"
    try:
        with db.begin_nested():
            db.add(
                m.IntegrationRecordLink(
                    provider_key=provider,
                    entity_type=entity_type,
                    external_id=external_id,
                    internal_id=internal_id,
                    household_id=household_id,
                    last_sync_run_id=run_id,
                )
            )
            db.flush()
        return "created"
    except IntegrityError:
        row = (
            db.query(m.IntegrationRecordLink)
            .filter(
                m.IntegrationRecordLink.provider_key == provider,
                m.IntegrationRecordLink.entity_type == entity_type,
                m.IntegrationRecordLink.external_id == external_id,
            )
            .first()
        )
        if row:
            row.last_sync_run_id = run_id
            row.updated_at = _now()
            return "updated"
        return "skipped"


def _touch_lineage(db: Session, entity_type: str, entity_id: str, provider: str, external_id: str):
    rec = (
        db.query(m.LineageRecord)
        .filter(m.LineageRecord.entity_type == entity_type, m.LineageRecord.entity_id == str(entity_id), m.LineageRecord.provider == provider)
        .first()
    )
    if rec:
        rec.updated_at = _now()
        rec.received_at = _now()
        rec.version = (rec.version or 1) + 1
        rec.data_quality_status = "FRESH"
        rec.source_record_id = external_id
        return
    db.add(
        m.LineageRecord(
            entity_type=entity_type,
            entity_id=str(entity_id),
            source=provider,
            provider=provider,
            source_record_id=external_id,
            as_of=utcnow().date() if hasattr(utcnow(), "date") else None,
            data_quality_status="FRESH",
        )
    )


def _apply_accounts(db, provider, items, run_id) -> tuple[int, int, int]:
    created = updated = skipped = 0
    for item in items:
        ext = item.get("external_id") or ""
        if not ext or item.get("unmatched") or ext == ORPHAN_EXTERNAL_ID:
            skipped += 1
            continue
        acct = db.query(m.Account).filter(m.Account.source_record_id == ext).first()
        if not acct:
            skipped += 1
            continue
        acct.received_at = _now()
        acct.data_quality_status = "FRESH"
        acct.version = (acct.version or 1) + 1
        acct.provider = provider
        action = _link(db, provider, "account", ext, acct.id, acct.household_id, run_id)
        _touch_lineage(db, "Account", str(acct.id), provider, ext)
        if action == "created":
            created += 1
        else:
            updated += 1
    return created, updated, skipped


def _apply_holdings(db, provider, items, run_id):
    created = updated = skipped = 0
    for item in items:
        ext = item.get("external_id") or ""
        if not ext:
            skipped += 1
            continue
        h = db.query(m.Holding).filter(m.Holding.source_record_id == ext).first()
        if not h:
            skipped += 1
            continue
        h.received_at = _now()
        h.data_quality_status = "FRESH"
        acct = db.query(m.Account).filter(m.Account.id == h.account_id).first()
        action = _link(db, provider, "holding", ext, h.id, acct.household_id if acct else None, run_id)
        _touch_lineage(db, "Holding", str(h.id), provider, ext)
        if action == "created":
            created += 1
        else:
            updated += 1
    return created, updated, skipped


def _apply_named(db, provider, entity_type, items, lookup, run_id):
    created = updated = skipped = 0
    for item in items:
        ext = item.get("external_id") or ""
        if not ext:
            skipped += 1
            continue
        row = lookup(item)
        if not row:
            skipped += 1
            continue
        hid = getattr(row, "household_id", None)
        action = _link(db, provider, entity_type, ext, row.id, hid, run_id)
        _touch_lineage(db, entity_type, str(row.id), provider, ext)
        if action == "created":
            created += 1
        else:
            updated += 1
    return created, updated, skipped


def run_sync(db: Session, provider_key: str, *, actor: str = "worker", actor_role: str = "SYSTEM", request_id: str = "", correlation_id: str = "") -> m.IntegrationSyncRun:
    request_id = request_id or str(__import__("uuid").uuid4())
    correlation_id = correlation_id or request_id
    provider = get_provider(provider_key)
    if not provider:
        raise ValueError("unknown_provider")
    run = m.IntegrationSyncRun(
        provider_key=provider_key,
        entity_type="mixed",
        status="running",
        request_id=request_id,
        correlation_id=correlation_id,
    )
    db.add(run)
    db.flush()
    conn = db.query(m.IntegrationConnection).filter(m.IntegrationConnection.provider_key == provider_key).first()
    try:
        with db.begin_nested():
            result = provider.execute("sync", {}, db=db, request_id=request_id, correlation_id=correlation_id)
            if not result.get("ok"):
                run.status = "failed"
                run.error = result.get("error") or "unavailable"
                run.finished_at = _now()
                if conn:
                    conn.status = "error"
                    conn.last_error = "Provider unavailable"
                    conn.last_request_id = request_id
                record_audit(
                    db,
                    actor=actor,
                    actor_role=actor_role,
                    action="integration_sync",
                    entity_type="Integration",
                    entity_id=provider_key,
                    after={"status": "failed", "error": run.error, "request_id": request_id, "correlation_id": correlation_id},
                    result="failed",
                    request_id=request_id,
                )
                return run

            payload = result.get("data") or {}
            received = 0
            created = updated = skipped = 0
            if provider.category == "financial":
                c, u, s = _apply_accounts(db, provider_key, payload.get("accounts") or [], run.id)
                created += c
                updated += u
                skipped += s
                received += len(payload.get("accounts") or [])
                c, u, s = _apply_holdings(db, provider_key, payload.get("holdings") or [], run.id)
                created += c
                updated += u
                skipped += s
                received += len(payload.get("holdings") or [])
                for lot in payload.get("tax_lots") or []:
                    received += 1
                    ext = lot.get("external_id") or ""
                    if not ext:
                        skipped += 1
                        continue
                    lot_row = db.query(m.TaxLot).filter(m.TaxLot.id == int(str(ext).split("-")[-1])).first() if str(ext).startswith("LOT-") else None
                    if not lot_row:
                        skipped += 1
                        continue
                    action = _link(db, provider_key, "tax_lot", ext, lot_row.id, None, run.id)
                    created += action == "created"
                    updated += action == "updated"
                for txn in payload.get("transactions") or []:
                    received += 1
                    ext = txn.get("external_id") or ""
                    if not ext:
                        skipped += 1
                        continue
                    txn_id = int(str(ext).split("-")[-1]) if str(ext).startswith("TXN-") else None
                    row = db.query(m.Transaction).filter(m.Transaction.id == txn_id).first() if txn_id else None
                    if not row:
                        skipped += 1
                        continue
                    action = _link(db, provider_key, "transaction", ext, row.id, None, run.id)
                    created += action == "created"
                    updated += action == "updated"
                reconcile_financial(db, provider_key, payload, request_id)
            elif provider.category == "business":
                received += len(payload.get("clients") or []) + len(payload.get("goals") or [])
                def hh_lookup(item):
                    return db.query(m.Household).filter(m.Household.name == item.get("household")).first()

                def goal_lookup(item):
                    ext = item.get("external_id") or ""
                    if ext.startswith("GOAL-"):
                        return db.query(m.Goal).filter(m.Goal.id == int(ext.split("-")[-1])).first()
                    return None

                c, u, s = _apply_named(db, provider_key, "household", payload.get("clients") or [], hh_lookup, run.id)
                created += c
                updated += u
                skipped += s
                c, u, s = _apply_named(db, provider_key, "goal", payload.get("goals") or [], goal_lookup, run.id)
                created += c
                updated += u
                skipped += s
            elif provider.category == "retirement":
                received += len(payload.get("participants") or []) + len(payload.get("plans") or [])

                def part_lookup(item):
                    ext = item.get("external_id") or ""
                    if ext.startswith("PART-"):
                        return db.query(m.Participant).filter(m.Participant.id == int(ext.split("-")[-1])).first()
                    return db.query(m.Participant).filter(m.Participant.email == item.get("email")).first()

                c, u, s = _apply_named(db, provider_key, "participant", payload.get("participants") or [], part_lookup, run.id)
                created += c
                updated += u
                skipped += s
            else:
                received = 1
                skipped = 1

            run.records_received = received
            run.created_count = created
            run.updated_count = updated
            run.skipped_count = skipped
            run.failed_count = 0
            run.status = "success"
            run.finished_at = _now()
            if conn:
                conn.status = "mock"
                conn.last_success_at = _now()
                conn.last_error = ""
                conn.last_request_id = request_id
                conn.freshness = "FRESH"
            record_audit(
                db,
                actor=actor,
                actor_role=actor_role,
                action="integration_sync",
                entity_type="Integration",
                entity_id=provider_key,
                after={
                    "status": "success",
                    "received": received,
                    "created": created,
                    "updated": updated,
                    "skipped": skipped,
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                },
                request_id=request_id,
            )
            return run
    except Exception as exc:
        log.warning(
            "integration_sync_failed provider=%s error_type=%s request_id=%s",
            provider_key,
            type(exc).__name__,
            request_id,
        )
        run.status = "failed"
        run.error = "unavailable"
        run.finished_at = _now()
        conn = db.query(m.IntegrationConnection).filter(m.IntegrationConnection.provider_key == provider_key).first()
        if conn:
            conn.status = "error"
            conn.last_error = "Sync failed"
        record_audit(
            db,
            actor=actor,
            actor_role=actor_role,
            action="integration_sync",
            entity_type="Integration",
            entity_id=provider_key,
            after={"status": "failed", "request_id": request_id},
            result="failed",
            request_id=request_id,
        )
        db.flush()
        return run
