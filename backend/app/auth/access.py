"""RBAC + relationship-based authorization. Never trust client-supplied IDs."""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models import entities as m

ROLES = ("CLIENT", "ADVISOR", "SPONSOR", "PARTICIPANT", "ADMIN")


def assigned_household_ids(db: Session, user: m.User) -> set[int]:
    if user.role == "ADMIN":
        return {row[0] for row in db.query(m.Household.id).all()}
    ids: set[int] = set()
    if user.household_id:
        ids.add(user.household_id)
    if user.role == "ADVISOR" and user.advisor_id:
        rows = db.query(m.Household.id).filter(m.Household.advisor_id == user.advisor_id).all()
        ids.update(r[0] for r in rows)
    return ids


def can_access_household(db: Session, user: m.User, household_id: Optional[int]) -> bool:
    if household_id is None:
        return False
    if user.role == "ADMIN":
        return True
    return household_id in assigned_household_ids(db, user)


def require_household(db: Session, user: m.User, household_id: int) -> m.Household:
    hh = db.query(m.Household).filter(m.Household.id == household_id).first()
    if not hh or not can_access_household(db, user, household_id):
        raise AppError("FORBIDDEN", "You are not authorized to access this household.", 403)
    return hh


def scoped_household(db: Session, user: m.User, household_id: Optional[int] = None) -> Optional[m.Household]:
    """Return the household in scope. Never falls back to an unrelated book of record."""
    if household_id is not None:
        return require_household(db, user, household_id)
    if user.household_id:
        return db.query(m.Household).filter(m.Household.id == user.household_id).first()
    if user.role == "ADVISOR" and user.advisor_id:
        return (
            db.query(m.Household)
            .filter(m.Household.advisor_id == user.advisor_id)
            .order_by(m.Household.id)
            .first()
        )
    if user.role == "ADMIN":
        return db.query(m.Household).order_by(m.Household.id).first()
    return None


def require_scoped_household(db: Session, user: m.User, household_id: Optional[int] = None) -> m.Household:
    hh = scoped_household(db, user, household_id)
    if not hh:
        raise AppError("FORBIDDEN", "No authorized household is available for this account.", 403)
    return hh


def filter_household_query(query, column, db: Session, user: m.User):
    if user.role == "ADMIN":
        return query
    ids = assigned_household_ids(db, user)
    if not ids:
        return query.filter(column == -1)
    return query.filter(column.in_(ids))


def can_access_plan(db: Session, user: m.User, plan: Optional[m.Plan]) -> bool:
    if user.role == "ADMIN":
        return True
    if not plan:
        return False
    if user.role == "SPONSOR":
        sponsor = db.query(m.Sponsor).filter(m.Sponsor.plan_id == plan.id).first()
        return bool(sponsor and sponsor.contact_name == user.full_name)
    if user.role == "PARTICIPANT":
        p = db.query(m.Participant).filter(m.Participant.plan_id == plan.id, m.Participant.email == user.email).first()
        return p is not None
    if user.role in {"ADVISOR", "CLIENT"}:
        return True
    return False


def own_participant(db: Session, user: m.User) -> Optional[m.Participant]:
    return db.query(m.Participant).filter(m.Participant.email == user.email).first()
