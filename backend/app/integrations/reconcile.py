"""Lightweight reconciliation. Never deletes book-of-record rows."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.integrations.feeds import ORPHAN_EXTERNAL_ID
from app.models import entities as m


def open_exception(db: Session, *, provider: str, exception_type: str, entity_type: str, household_id, external_id: str, detail: dict, request_id: str, severity: str = "info"):
    existing = (
        db.query(m.ReconciliationException)
        .filter(
            m.ReconciliationException.provider_key == provider,
            m.ReconciliationException.exception_type == exception_type,
            m.ReconciliationException.external_id == external_id,
            m.ReconciliationException.status == "open",
        )
        .first()
    )
    if existing:
        existing.detail = detail
        existing.request_id = request_id
        return existing
    row = m.ReconciliationException(
        provider_key=provider,
        exception_type=exception_type,
        entity_type=entity_type,
        household_id=household_id,
        external_id=external_id,
        detail=detail,
        status="open",
        severity=severity,
        request_id=request_id,
    )
    db.add(row)
    return row


def reconcile_financial(db: Session, provider: str, payload: dict, request_id: str) -> int:
    created = 0
    hh_ids = {h.name: h.id for h in db.query(m.Household).all()}
    for acct in payload.get("accounts") or []:
        if acct.get("unmatched") or acct.get("external_id") == ORPHAN_EXTERNAL_ID:
            if provider != "custodian":
                continue
            open_exception(
                db,
                provider=provider,
                exception_type="unmatched_inbound",
                entity_type="account",
                household_id=hh_ids.get(acct.get("household")),
                external_id=acct.get("external_id") or "",
                detail={"name": acct.get("name"), "reason": "Feed record has no book-of-record match. Not inserted."},
                request_id=request_id,
                severity="warn",
            )
            created += 1
            continue
        book = db.query(m.Account).filter(m.Account.source_record_id == acct.get("external_id")).first()
        if not book:
            open_exception(
                db,
                provider=provider,
                exception_type="missing_in_book",
                entity_type="account",
                household_id=hh_ids.get(acct.get("household")),
                external_id=acct.get("external_id") or "",
                detail={"name": acct.get("name")},
                request_id=request_id,
                severity="warn",
            )
            created += 1
            continue
        feed_mv = float(acct.get("market_value") or 0)
        if abs(feed_mv - float(book.market_value or 0)) > 1:
            open_exception(
                db,
                provider=provider,
                exception_type="balance_mismatch",
                entity_type="account",
                household_id=book.household_id,
                external_id=acct.get("external_id") or "",
                detail={"book": book.market_value, "feed": feed_mv},
                request_id=request_id,
                severity="warn",
            )
            created += 1
    return created
