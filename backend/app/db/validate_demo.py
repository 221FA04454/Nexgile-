"""Validate relational demo data. Exit non-zero on orphaned or missing core records."""
from __future__ import annotations

import sys

from app.db.session import SessionLocal, get_engine
from app.models import entities as m
from app import models  # noqa: F401


class Failures(list):
    def check(self, cond: bool, msg: str) -> None:
        if not cond:
            self.append(msg)


def validate(db) -> list[str]:
    fails = Failures()
    households = db.query(m.Household).all()
    names = {h.name for h in households}
    fails.check(len(households) >= 3, "expected at least 3 households")
    fails.check("Morgan Family" in names, "Morgan Family missing")
    fails.check("Chen Family" in names, "Chen Family missing")
    fails.check("Shah Family" in names, "Shah Family missing")

    users = db.query(m.User).all()
    fails.check(any(u.role == "CLIENT" and u.email == "alex.morgan@nexgile.demo" for u in users), "Alex Morgan client missing")
    fails.check(any(u.role == "ADVISOR" for u in users), "advisor user missing")
    fails.check(any(u.role == "SPONSOR" for u in users), "sponsor user missing")
    fails.check(any(u.role == "PARTICIPANT" for u in users), "participant user missing")
    fails.check(any(u.role == "ADMIN" for u in users), "admin user missing")

    for u in users:
        if u.role == "CLIENT":
            fails.check(u.household_id is not None, f"client {u.email} has no household")
            hh = db.query(m.Household).filter(m.Household.id == u.household_id).first()
            fails.check(hh is not None, f"client {u.email} household FK broken")

    accounts = db.query(m.Account).all()
    fails.check(len(accounts) >= 10, "too few accounts")
    hh_ids = {h.id for h in households}
    for a in accounts:
        fails.check(a.household_id in hh_ids, f"account {a.id} orphaned household")

    holdings = db.query(m.Holding).all()
    fails.check(len(holdings) >= 20, "too few holdings")
    acct_ids = {a.id for a in accounts}
    for h in holdings:
        fails.check(h.account_id in acct_ids, f"holding {h.id} orphaned account")

    lots = db.query(m.TaxLot).all()
    holding_ids = {h.id for h in holdings}
    fails.check(len(lots) >= 10, "too few tax lots")
    for lot in lots:
        fails.check(lot.holding_id in holding_ids, f"tax lot {lot.id} orphaned holding")

    portfolios = db.query(m.Portfolio).all()
    fails.check(len(portfolios) >= 3, "expected a portfolio per demo household")
    for p in portfolios:
        fails.check(p.household_id in hh_ids, f"portfolio {p.id} orphaned")
        owned = [a.id for a in accounts if a.household_id == p.household_id]
        owned_holdings = [h for h in holdings if h.account_id in owned]
        fails.check(len(owned_holdings) >= 1, f"portfolio household {p.household_id} has no holdings")

    goals = db.query(m.Goal).all()
    fails.check(len(goals) >= 4, "too few goals")
    for g in goals:
        fails.check(g.household_id in hh_ids, f"goal {g.id} orphaned")

    tax_opps = db.query(m.TaxOpportunity).all()
    fails.check(len(tax_opps) >= 4, "too few tax opportunities")
    for t in tax_opps:
        fails.check(t.household_id in hh_ids, f"tax opportunity {t.id} orphaned")

    harvests = db.query(m.Harvest).all()
    for hv in harvests:
        fails.check(hv.household_id in hh_ids, f"harvest {hv.id} orphaned")
        if hv.holding_id:
            fails.check(hv.holding_id in holding_ids, f"harvest {hv.id} holding FK broken")

    docs = db.query(m.Document).all()
    fails.check(len(docs) >= 8, "too few documents")
    for d in docs:
        fails.check(d.household_id in hh_ids, f"document {d.id} orphaned")

    approvals = db.query(m.Approval).all()
    fails.check(len(approvals) >= 1, "expected at least one approval")
    for a in approvals:
        if a.household_id:
            fails.check(a.household_id in hh_ids, f"approval {a.id} orphaned")

    audits = db.query(m.AuditEvent).all()
    fails.check(len(audits) >= 1, "expected audit events from seed")

    morgan = next((h for h in households if h.name == "Morgan Family"), None)
    fails.check(morgan is not None, "Morgan Family missing for account-type check")
    if morgan:
        types = {a.account_type for a in accounts if a.household_id == morgan.id}
        for required in {"brokerage", "401k", "roth_ira", "traditional_ira", "trust", "cash"}:
            fails.check(required in types, f"Morgan missing account type {required}")

    return fails


def main() -> int:
    get_engine()
    db = SessionLocal()
    try:
        failures = validate(db)
    finally:
        db.close()
    if failures:
        print("DEMO DATA VALIDATION FAILED")
        for item in failures:
            print(f" - {item}")
        return 1
    print("DEMO DATA VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
