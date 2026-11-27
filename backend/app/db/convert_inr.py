"""Idempotent INR book conversion for existing demo rows. Does not duplicate households."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.ai.prompts import DEFAULT_PROMPTS, WEALTH_ASSISTANT_V1
from app.core.currency import DEFAULT_CURRENCY
from app.models import entities as m

NARRATIVE_REPLACEMENTS = (
    ("$210k in today's dollars", "₹2,10,000 in today's rupees"),
    ("$3.0M target", "₹30,00,000 target"),
    ("$42,600 remaining", "₹42,600 remaining"),
    ("$48k from", "₹48,000 from"),
    ("$12k DAF", "₹12,000 DAF"),
    ("today's dollars", "today's rupees"),
    ("2026 dollars", "2026 rupees"),
)


def _rewrite(text: str | None) -> str | None:
    if not text:
        return text
    out = text
    for old, new in NARRATIVE_REPLACEMENTS:
        out = out.replace(old, new)
    return out


def apply_inr_book(db: Session) -> None:
    for acct in db.query(m.Account).all():
        if (acct.currency or "").upper() != DEFAULT_CURRENCY:
            acct.currency = DEFAULT_CURRENCY
    for goal in db.query(m.Goal).all():
        goal.notes = _rewrite(goal.notes)
    for rec in db.query(m.Recommendation).all():
        rec.body = _rewrite(rec.body)
        rec.title = _rewrite(rec.title)
    for opp in db.query(m.TaxOpportunity).all():
        opp.detail = _rewrite(opp.detail)
    for msg in db.query(m.Message).all():
        msg.body = _rewrite(msg.body)
        msg.subject = _rewrite(msg.subject)
    for tmpl in db.query(m.PromptTemplate).filter(m.PromptTemplate.active.is_(True)).all():
        if "INR" not in (tmpl.template or "") and tmpl.name == "wealth_assistant_v1":
            tmpl.template = WEALTH_ASSISTANT_V1
            tmpl.version = "v1-inr"
        elif tmpl.name != "wealth_assistant_v1":
            seeded = next((p for p in DEFAULT_PROMPTS if p["name"] == tmpl.name), None)
            if seeded and "INR" in seeded["template"] and "INR" not in (tmpl.template or ""):
                tmpl.template = seeded["template"]
    db.flush()
