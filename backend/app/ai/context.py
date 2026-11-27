"""Authorized PostgreSQL context for the AI orchestrator. No hardcoded currency amounts."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth.access import assigned_household_ids
from app.models import entities as m
from app.services import wealth as w


def get_portfolio_context(db: Session, user: m.User) -> dict:
    return w.portfolio_payload(db, user)


def get_goal_context(db: Session, user: m.User) -> dict:
    return w.goals_payload(db, user)


def get_tax_context(db: Session, user: m.User) -> dict:
    return w.tax_payload(db, user)


def get_retirement_context(db: Session, user: m.User) -> dict:
    return w.retirement_payload(db, user)


def get_estate_context(db: Session, user: m.User) -> dict:
    return w.estate_payload(db, user)


def get_philanthropy_context(db: Session, user: m.User) -> dict:
    return w.philanthropy_payload(db, user)


def get_account_context(db: Session, user: m.User) -> dict:
    return w.accounts_payload(db, user)


def get_activity_context(db: Session, user: m.User) -> dict:
    dash = w.dashboard(db, user)
    return {"activity": dash.get("activity") or [], "household": dash.get("household")}


def get_document_context(db: Session, user: m.User) -> dict:
    return w.documents_payload(db, user)


def build_authorized_context(db: Session, user: m.User, intent: str) -> dict:
    hh = w.household_for_user(db, user)
    ctx = {
        "household": {"id": hh.id, "name": hh.name} if hh else None,
        "role": user.role,
        "allowed_household_ids": sorted(assigned_household_ids(db, user)),
    }
    loaders = {
        "PORTFOLIO_PERFORMANCE": ("portfolio", get_portfolio_context),
        "PORTFOLIO_ALLOCATION": ("portfolio", get_portfolio_context),
        "GOAL_PROGRESS": ("goals", get_goal_context),
        "RETIREMENT_READINESS": (("goals", get_goal_context), ("retirement", get_retirement_context)),
        "TAX_OPPORTUNITY": ("tax", get_tax_context),
        "DOCUMENT_QUERY": ("documents", get_document_context),
        "ESTATE_STATUS": ("estate", get_estate_context),
        "PHILANTHROPY": ("philanthropy", get_philanthropy_context),
        "ACCOUNT_SUMMARY": ("accounts", get_account_context),
        "RECENT_ACTIVITY": ("activity", get_activity_context),
        "GENERAL_WEALTH_QUERY": ("dashboard", w.dashboard),
    }
    spec = loaders.get(intent, ("dashboard", w.dashboard))
    items = spec if isinstance(spec[0], tuple) else (spec,)
    for key, fn in items:
        ctx[key] = fn(db, user)
    if intent in {"GENERAL_WEALTH_QUERY", "PORTFOLIO_PERFORMANCE"}:
        ctx.setdefault("dashboard", w.dashboard(db, user))
    return ctx


def mentioned_unauthorized_household(db: Session, user: m.User, message: str) -> m.Household | None:
    allowed = assigned_household_ids(db, user)
    q = (message or "").lower()
    for hh in db.query(m.Household).all():
        if hh.id in allowed:
            continue
        names = [hh.name.lower(), (hh.primary_client_name or "").lower()]
        if any(n and n in q for n in names if n):
            return hh
    return None
