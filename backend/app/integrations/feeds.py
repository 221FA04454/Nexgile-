"""Mock feeds derived from the existing PostgreSQL book — never a second dataset."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import entities as m

ORPHAN_EXTERNAL_ID = "SCHWAB-ORPHAN-UNMATCHED"


def household_map(db: Session) -> dict[str, m.Household]:
    return {h.name: h for h in db.query(m.Household).all()}


def financial_snapshot(db: Session) -> dict:
    households = household_map(db)
    accounts_rows = db.query(m.Account).all()
    holdings_rows = db.query(m.Holding).all()
    lots_rows = db.query(m.TaxLot).all()
    txn_rows = db.query(m.Transaction).all()
    holdings_by_acct: dict[int, list] = {}
    for h in holdings_rows:
        holdings_by_acct.setdefault(h.account_id, []).append(h)
    lots_by_holding: dict[int, list] = {}
    for lot in lots_rows:
        lots_by_holding.setdefault(lot.holding_id, []).append(lot)
    txns_by_acct: dict[int, list] = {}
    for txn in txn_rows:
        txns_by_acct.setdefault(txn.account_id, []).append(txn)
    accounts = []
    holdings = []
    tax_lots = []
    transactions = []
    for acct in accounts_rows:
        hh = next((h for h in households.values() if h.id == acct.household_id), None)
        ext = acct.source_record_id or f"ACCT-{acct.id}"
        accounts.append(
            {
                "external_id": ext,
                "household": hh.name if hh else "",
                "name": acct.name,
                "account_type": acct.account_type,
                "masked": acct.account_number_masked,
                "market_value": acct.market_value,
                "cash_balance": acct.cash_balance,
                "cost_basis": acct.cost_basis,
            }
        )
        for h in holdings_by_acct.get(acct.id, []):
            hid = h.source_record_id or f"POS-{h.symbol}-{acct.id}"
            holdings.append(
                {
                    "external_id": hid,
                    "account_external_id": ext,
                    "symbol": h.symbol,
                    "name": h.name,
                    "quantity": h.quantity,
                    "price": h.price,
                    "market_value": round((h.quantity or 0) * (h.price or 0), 2),
                }
            )
            for lot in lots_by_holding.get(h.id, []):
                tax_lots.append(
                    {
                        "external_id": f"LOT-{lot.id}",
                        "holding_external_id": hid,
                        "quantity": lot.quantity,
                        "cost_per_share": lot.cost_per_share,
                    }
                )
        for txn in txns_by_acct.get(acct.id, []):
            transactions.append(
                {
                    "external_id": f"TXN-{txn.id}",
                    "account_external_id": ext,
                    "description": txn.description,
                    "amount": txn.amount,
                    "occurred_on": str(txn.occurred_on),
                }
            )
    accounts.append(
        {
            "external_id": ORPHAN_EXTERNAL_ID,
            "household": "Morgan Family",
            "name": "Unmatched custodian shadow account",
            "account_type": "Brokerage",
            "masked": "****0000",
            "market_value": 0,
            "cash_balance": 0,
            "cost_basis": 0,
            "unmatched": True,
        }
    )
    return {
        "accounts": accounts,
        "holdings": holdings,
        "tax_lots": tax_lots,
        "transactions": transactions,
        "prices": [{"symbol": h["symbol"], "price": h["price"]} for h in holdings],
        "orders": [{"status": "sandbox", "executed": False, "book_of_record_modified": False}],
        "alternatives": [a for a in accounts if "alt" in (a.get("account_type") or "").lower() or "private" in (a.get("name") or "").lower()],
    }


def business_snapshot(db: Session) -> dict:
    clients = []
    goals = []
    for hh in db.query(m.Household).all():
        clients.append(
            {
                "external_id": f"HH-{hh.id}",
                "household": hh.name,
                "primary_client": hh.primary_client_name,
                "risk_profile": hh.risk_profile,
                "advisor_id": hh.advisor_id,
            }
        )
        for g in db.query(m.Goal).filter(m.Goal.household_id == hh.id).all():
            goals.append(
                {
                    "external_id": f"GOAL-{g.id}",
                    "household": hh.name,
                    "name": g.name,
                    "target": g.target_amount,
                    "current": g.current_amount,
                }
            )
    return {"clients": clients, "households": clients, "goals": goals, "tasks": [], "tax": [], "estate": [], "beneficiaries": []}


def retirement_snapshot(db: Session) -> dict:
    participants = []
    for p in db.query(m.Participant).all():
        participants.append(
            {
                "external_id": f"PART-{p.id}",
                "name": p.name,
                "email": p.email,
                "balance": p.balance,
                "match": p.employer_match_ytd,
                "vested_pct": p.vested_pct,
            }
        )
    plans = [{"external_id": f"PLAN-{pl.id}", "name": pl.name} for pl in db.query(m.Plan).all()]
    return {
        "plans": plans,
        "participants": participants,
        "contributions": [],
        "loans": [],
        "distributions": [],
        "investment_options": [],
        "census": participants,
        "filings": [{"form": "5500", "status": "sandbox"}],
    }
