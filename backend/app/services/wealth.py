from datetime import datetime, date, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.auth.access import assigned_household_ids, can_access_household, own_participant, scoped_household
from app.calculations import engine as calc
from app.core.config import get_settings
from app.core.currency import currency_meta, format_inr, with_currency
from app.core.errors import AppError
from app.models import entities as m
from app.services.audit import lineage_payload

AS_OF = "2026-09-07"
INVESTMENT_ACCOUNT_TYPES = {"brokerage", "401k", "roth_ira", "traditional_ira", "trust", "cash", "ira"}


def lineage(version: int = 1, updated_at=None, data_quality_status: str = "FRESH", **kwargs) -> dict:
    return {
        **lineage_payload(
            as_of=AS_OF,
            updated_at=updated_at or datetime.now(timezone.utc),
            version=version,
            data_quality_status=data_quality_status,
            provider=get_settings().data_provider,
            **kwargs,
        ),
        **currency_meta(),
    }


def household_for_user(db: Session, user: m.User, household_id: Optional[int] = None) -> Optional[m.Household]:
    return scoped_household(db, user, household_id)


def _empty_book(user: m.User) -> dict:
    return with_currency({
        "household": {"id": None, "name": "No household assigned", "risk_profile": ""},
        "client": {"name": user.full_name, "role": user.role},
        "net_worth": {"total": 0, "change_today": 0, "change_today_pct": 0, "change_ytd": 0, "change_ytd_pct": 0, "assets": 0, "liabilities": 0},
        "portfolio": {"invested_assets": 0, "daily_change": 0, "daily_change_pct": 0, "ytd_return": 0},
        "cash": {"available": 0, "emergency_reserve": 0, "upcoming_needs": 0, "label": ""},
        "goals": [],
        "allocation": [],
        "tax_opportunities": [],
        "insights": [],
        "activity": [],
        "lineage": lineage(),
        "balance_sheet": {"invested_assets": 0, "other_assets": 0, "liabilities": 0, "net_worth": 0},
    })


def _holdings(db: Session, household_id: int):
    acct_ids = [
        a.id
        for a in db.query(m.Account).filter(
            m.Account.household_id == household_id,
            m.Account.account_type.in_(INVESTMENT_ACCOUNT_TYPES),
        ).all()
    ]
    if not acct_ids:
        return []
    return db.query(m.Holding).filter(m.Holding.account_id.in_(acct_ids)).all()


def _ytd_from_performance(db: Session, household_id: int, invested: float) -> tuple[float, float]:
    portfolio = db.query(m.Portfolio).filter(m.Portfolio.household_id == household_id).first()
    if not portfolio:
        return 0.0, 0.0
    points = (
        db.query(m.PerformancePoint)
        .filter(m.PerformancePoint.portfolio_id == portfolio.id)
        .order_by(m.PerformancePoint.as_of)
        .all()
    )
    if len(points) < 2:
        return 0.0, 0.0
    start = points[0].market_value or 0
    end = points[-1].market_value or invested
    change = round(end - start, 2)
    pct = round((end / start - 1) * 100, 1) if start else 0.0
    return change, pct


def dashboard(db: Session, user: m.User) -> dict:
    hh = household_for_user(db, user)
    if not hh:
        return _empty_book(user)
    accounts = db.query(m.Account).filter(m.Account.household_id == hh.id).all()
    holdings = _holdings(db, hh.id)
    summary = calc.holdings_summary(holdings)
    goals = db.query(m.Goal).filter(m.Goal.household_id == hh.id).all()
    recs = db.query(m.Recommendation).filter(m.Recommendation.household_id == hh.id).all()
    txns = (
        db.query(m.Transaction)
        .join(m.Account, m.Transaction.account_id == m.Account.id)
        .filter(m.Account.household_id == hh.id)
        .order_by(m.Transaction.occurred_on.desc())
        .limit(8)
        .all()
    )
    tax_opps = db.query(m.TaxOpportunity).filter(m.TaxOpportunity.household_id == hh.id).all()
    cash = next((a for a in accounts if a.account_type == "cash"), None)
    real_estate = hh.other_assets or sum((a.market_value or 0) for a in accounts if a.account_type == "real_estate")
    mortgage = hh.liabilities or sum((a.market_value or 0) for a in accounts if a.account_type == "liability")
    invested = summary["total_market_value"]
    ytd_change, ytd_pct = _ytd_from_performance(db, hh.id, invested)
    net_worth = invested + real_estate - mortgage
    goal_cards = []
    for g in goals:
        goal_cards.append(
            {
                "id": g.id,
                "name": g.name,
                "category": g.category,
                "target": g.target_amount,
                "current": g.current_amount,
                "pct": calc.funding_pct(g.current_amount, g.target_amount),
                "projected_status": g.projected_status,
                "probability": g.probability,
                "target_date": str(g.target_date),
            }
        )
    return with_currency({
        "household": {"id": hh.id, "name": hh.name, "risk_profile": hh.risk_profile},
        "client": {"name": user.full_name, "role": user.role},
        "net_worth": {
            "total": round(net_worth, 2),
            "change_today": round(summary["day_change"], 2),
            "change_today_pct": summary["day_change_pct"],
            "change_ytd": ytd_change,
            "change_ytd_pct": ytd_pct,
            "assets": round(invested + real_estate, 2),
            "liabilities": mortgage,
        },
        "portfolio": {
            "invested_assets": invested,
            "daily_change": summary["day_change"],
            "daily_change_pct": summary["day_change_pct"],
            "ytd_return": summary["ytd_return_pct"],
        },
        "cash": {
            "available": cash.cash_balance if cash else 0,
            "emergency_reserve": hh.emergency_reserve or 0,
            "upcoming_needs": hh.upcoming_needs or 0,
            "label": hh.liquidity_label or "",
        },
        "goals": goal_cards,
        "allocation": summary["allocation"],
        "tax_opportunities": [
            {"id": t.id, "type": t.opportunity_type, "title": t.title, "detail": t.detail, "benefit": t.estimated_benefit, "status": t.status}
            for t in tax_opps
        ],
        "insights": [
            {"title": r.title, "body": r.body, "category": r.category, "severity": r.severity}
            for r in recs
        ],
        "activity": [
            {
                "id": t.id,
                "type": t.txn_type,
                "description": t.description,
                "amount": t.amount,
                "date": str(t.occurred_on),
                "actor": t.actor,
            }
            for t in txns
        ],
        "lineage": lineage(3, updated_at=next((a.updated_at for a in accounts if a.updated_at), None)),
        "balance_sheet": {
            "invested_assets": invested,
            "other_assets": real_estate,
            "liabilities": mortgage,
            "net_worth": round(net_worth, 2),
        },
    })


def accounts_payload(db: Session, user: m.User) -> dict:
    hh = household_for_user(db, user)
    if not hh:
        return with_currency({
            "accounts": [],
            "total_market_value": 0,
            "balance_sheet": {"invested_assets": 0, "other_assets": 0, "liabilities": 0, "net_worth": 0},
            "lineage": lineage(),
        })
    accounts = db.query(m.Account).filter(m.Account.household_id == hh.id).all()
    rows = []
    for a in accounts:
        rows.append(
            {
                "id": a.id,
                "name": a.name,
                "type": a.account_type,
                "masked": a.account_number_masked,
                "tax_status": a.tax_status,
                "owner": a.owner_name,
                "cash": a.cash_balance,
                "market_value": a.market_value,
                "cost_basis": a.cost_basis,
                "unrealized": round((a.market_value or 0) - (a.cost_basis or 0), 2),
                "status": a.status,
                "provider": a.provider,
                "currency": a.currency or "INR",
                "as_of": str(a.as_of),
                "source": a.source,
                "version": a.version,
            }
        )
    return with_currency({
        "accounts": rows,
        "total_market_value": round(sum((a.market_value or 0) for a in accounts if a.account_type in INVESTMENT_ACCOUNT_TYPES), 2),
        "balance_sheet": {
            "invested_assets": round(sum((a.market_value or 0) for a in accounts if a.account_type in INVESTMENT_ACCOUNT_TYPES), 2),
            "other_assets": hh.other_assets or 0,
            "liabilities": hh.liabilities or 0,
            "net_worth": round(
                sum((a.market_value or 0) for a in accounts if a.account_type in INVESTMENT_ACCOUNT_TYPES)
                + (hh.other_assets or 0)
                - (hh.liabilities or 0),
                2,
            ),
        },
        "lineage": lineage(),
    })


def portfolio_payload(db: Session, user: m.User, portfolio_id: int = 1) -> dict:
    hh = household_for_user(db, user)
    if not hh:
        empty = calc.holdings_summary([])
        return with_currency({
            "portfolio": {"id": None, "name": "No portfolio", "strategy": ""},
            "summary": empty,
            "risk": {"score": 0, "label": "n/a"},
            "targets": {},
            "benchmark": {"name": "", "ytd": 0, "one_year": 0, "portfolio_ytd": 0, "excess_ytd": 0},
            "performance": [],
            "top_holdings": [],
            "lineage": lineage(),
        })
    portfolio = (
        db.query(m.Portfolio)
        .filter(m.Portfolio.household_id == hh.id, m.Portfolio.id == portfolio_id)
        .first()
        or db.query(m.Portfolio).filter(m.Portfolio.household_id == hh.id).first()
    )
    holdings = _holdings(db, hh.id)
    summary = calc.holdings_summary(holdings)
    points = []
    if portfolio:
        points = (
            db.query(m.PerformancePoint)
            .filter(m.PerformancePoint.portfolio_id == portfolio.id)
            .order_by(m.PerformancePoint.as_of)
            .all()
        )
    bench = db.query(m.Benchmark).first()
    equity = next((a["pct"] for a in summary["allocation"] if a["name"] == "Equities"), 0)
    alts = next((a["pct"] for a in summary["allocation"] if a["name"] == "Alternatives"), 0)
    max_weight = max((h["weight"] for h in summary["holdings"]), default=0)
    risk = calc.risk_score(equity, alts, max_weight)
    targets = {
        "equity": portfolio.target_equity if portfolio else 0.62,
        "fixed_income": portfolio.target_fixed_income if portfolio else 0.22,
        "alternatives": portfolio.target_alternatives if portfolio else 0.08,
        "cash": portfolio.target_cash if portfolio else 0.06,
        "other": portfolio.target_other if portfolio else 0.02,
    }
    return with_currency({
        "portfolio": {
            "id": portfolio.id if portfolio else 1,
            "name": portfolio.name if portfolio else "Household Portfolio",
            "strategy": portfolio.strategy if portfolio else "Moderate Growth",
        },
        "summary": summary,
        "risk": risk,
        "targets": targets,
        "benchmark": {
            "name": bench.name if bench else "60/40",
            "ytd": bench.ytd_return_pct if bench else 11.4,
            "one_year": bench.one_year_return_pct if bench else 14.8,
            "portfolio_ytd": summary["ytd_return_pct"],
            "excess_ytd": round(summary["ytd_return_pct"] - (bench.ytd_return_pct if bench else 11.4), 2),
        },
        "performance": [
            {"date": str(p.as_of), "portfolio": p.market_value, "benchmark": p.benchmark_value} for p in points
        ],
        "top_holdings": summary["holdings"][:8],
        "lineage": lineage(portfolio.version if portfolio else 1),
    })


def goals_payload(db: Session, user: m.User) -> dict:
    hh = household_for_user(db, user)
    if not hh:
        return with_currency({"goals": [], "monte_carlo": calc.monte_carlo(0, 0), "lineage": lineage()})
    goals = db.query(m.Goal).filter(m.Goal.household_id == hh.id).all()
    cards = []
    for g in goals:
        years = max(0, (g.target_date.year + (g.target_date.month - 1) / 12) - 2026.7)
        scenarios = db.query(m.Scenario).filter(m.Scenario.goal_id == g.id).all()
        cards.append(
            {
                "id": g.id,
                "name": g.name,
                "category": g.category,
                "target": g.target_amount,
                "current": g.current_amount,
                "pct": calc.funding_pct(g.current_amount, g.target_amount),
                "probability": g.probability,
                "projected_status": g.projected_status,
                "target_date": str(g.target_date),
                "linked_accounts": g.linked_accounts or [],
                "annual_contribution": g.annual_contribution,
                "notes": g.notes,
                "forecast": calc.goal_projection(g.current_amount, g.annual_contribution or 0, years),
                "book_of_record_isolated_scenarios": True,
                "scenarios": [
                    {
                        "name": s.name,
                        "growth_rate": s.growth_rate,
                        "projected_value": s.projected_value,
                        "probability": s.probability,
                        "isolated": s.isolated,
                    }
                    for s in scenarios
                ],
            }
        )
    retirement = next((g for g in goals if (g.category or "").lower() == "retirement"), goals[0] if goals else None)
    mc = calc.monte_carlo(
        retirement.current_amount if retirement else 0,
        retirement.annual_contribution if retirement else 0,
        target=retirement.target_amount if retirement else 3000000,
    )
    return with_currency({"goals": cards, "monte_carlo": mc, "lineage": lineage()})


def tax_payload(db: Session, user: m.User) -> dict:
    hh = household_for_user(db, user)
    if not hh:
        return {
            "estimated_liability": 0,
            "capital_gains_budget": {"used": 0, "remaining": 0, "limit": 0},
            "carryforward_losses": 0,
            "opportunities": [],
            "harvests": [],
            "rmd": {"status": "not_required", "required": 0, "taken": 0, "deadline": None},
            "wash_sales": [],
            "liability_method": calc.estimated_tax_impact(0, True),
            "lineage": lineage(),
        }
    opps = db.query(m.TaxOpportunity).filter(m.TaxOpportunity.household_id == hh.id).all()
    harvests = db.query(m.Harvest).filter(m.Harvest.household_id == hh.id).all()
    rmd = db.query(m.RMD).filter(m.RMD.household_id == hh.id).first()
    windows = db.query(m.WashSaleWindow).filter(m.WashSaleWindow.household_id == hh.id).all()
    holdings = _holdings(db, hh.id)
    summary = calc.holdings_summary(holdings)
    liability = calc.estimated_tax_impact(max(summary["unrealized_gain_loss"] * 0.08, 0), True)
    used = hh.capital_gains_budget_used or 0
    limit = hh.capital_gains_budget_limit or 0
    return with_currency({
        "estimated_liability": hh.estimated_tax_liability if hh.estimated_tax_liability is not None else liability.get("estimated_tax", 0),
        "capital_gains_budget": {"used": used, "remaining": round(max(limit - used, 0), 2), "limit": limit},
        "carryforward_losses": hh.carryforward_losses or 0,
        "opportunities": [
            {
                "id": o.id,
                "type": o.opportunity_type,
                "title": o.title,
                "detail": o.detail,
                "benefit": o.estimated_benefit,
                "status": o.status,
                "requires_approval": o.requires_approval,
            }
            for o in opps
        ],
        "harvests": [
            {
                "id": h.id,
                "symbol": h.symbol,
                "name": h.security_name,
                "unrealized_loss": h.unrealized_loss,
                "potential_tax_benefit": h.potential_tax_benefit,
                "wash_sale_status": h.wash_sale_status,
                "replacement": h.replacement_security,
                "status": h.status,
            }
            for h in harvests
        ],
        "rmd": {
            "status": rmd.status if rmd else "not_required",
            "required": rmd.required_amount if rmd else 0,
            "taken": rmd.taken_ytd if rmd else 0,
            "deadline": str(rmd.deadline) if rmd else None,
        },
        "wash_sales": [
            {"symbol": w.symbol, "start": str(w.window_start), "end": str(w.window_end), "restricted": w.restricted}
            for w in windows
        ],
        "liability_method": liability,
        "lineage": lineage(),
    })


def estate_payload(db: Session, user: m.User) -> dict:
    hh = household_for_user(db, user)
    if not hh:
        return {
            "readiness_score": 0,
            "attorney": "",
            "last_review": None,
            "next_review": None,
            "estate_tax_exposure": 0,
            "documents": {"will": "missing", "trust": "missing", "power_of_attorney": "missing", "healthcare_directive": "missing"},
            "trusts": [],
            "beneficiaries": [],
            "reminders": [],
            "lineage": lineage(),
        }
    plan = db.query(m.EstatePlan).filter(m.EstatePlan.household_id == hh.id).first()
    trusts = db.query(m.Trust).filter(m.Trust.household_id == hh.id).all()
    bens = db.query(m.Beneficiary).filter(m.Beneficiary.household_id == hh.id).all()
    return {
        "readiness_score": plan.readiness_score if plan else 0,
        "attorney": plan.attorney_name if plan else "",
        "last_review": str(plan.last_review) if plan else None,
        "next_review": str(plan.next_review) if plan else None,
        "estate_tax_exposure": plan.estate_tax_exposure if plan else 0,
        "documents": {
            "will": plan.will_status if plan else "missing",
            "trust": plan.trust_status if plan else "missing",
            "power_of_attorney": plan.poa_status if plan else "missing",
            "healthcare_directive": plan.healthcare_directive_status if plan else "missing",
        },
        "trusts": [
            {"id": t.id, "name": t.name, "type": t.trust_type, "trustee": t.trustee, "assets": t.assets, "funded": t.funded}
            for t in trusts
        ],
        "beneficiaries": [
            {
                "id": b.id,
                "name": b.name,
                "relationship": b.relationship,
                "account": b.account_or_trust,
                "share_pct": b.share_pct,
                "contingent": b.contingent,
                "last_reviewed": str(b.last_reviewed),
            }
            for b in bens
        ],
        "reminders": [
            {"title": "Healthcare directive refresh", "due": "2026-09-30", "severity": "high"},
            {"title": "Annual beneficiary confirmation", "due": "2026-11-02", "severity": "medium"},
        ],
        "lineage": lineage(),
    }


def philanthropy_payload(db: Session, user: m.User) -> dict:
    hh = household_for_user(db, user)
    if not hh:
        return {
            "plan": {"mission": "", "annual_target": 0, "donated_ytd": 0, "remaining": 0, "tax_deduction_estimate": 0},
            "daf": {"name": "", "balance": 0, "ytd_grants": 0, "sponsor": ""},
            "foundation": {"status": "not_established", "note": ""},
            "qcd": {"eligible": False, "reason": ""},
            "gifts": [],
            "lineage": lineage(),
        }
    daf = db.query(m.DAF).filter(m.DAF.household_id == hh.id).first()
    gifts = db.query(m.Gift).filter(m.Gift.household_id == hh.id).all()
    donated = sum(g.amount for g in gifts if g.status == "completed")
    return {
        "plan": {
            "mission": "Education access and coastal conservation in California.",
            "annual_target": 45000,
            "donated_ytd": donated,
            "remaining": 45000 - donated,
            "tax_deduction_estimate": sum(g.tax_deduction_estimate or 0 for g in gifts),
        },
        "daf": {
            "name": daf.name if daf else "DAF",
            "balance": daf.balance if daf else 0,
            "ytd_grants": daf.ytd_grants if daf else 0,
            "sponsor": daf.sponsor if daf else "",
        },
        "foundation": {"status": "not_established", "note": "ILIT and private foundation remain unfunded placeholders."},
        "qcd": {"eligible": False, "reason": "QCD available after age 70½. First eligible year projected 2049."},
        "gifts": [
            {
                "id": g.id,
                "charity": g.charity_name,
                "type": g.gift_type,
                "amount": g.amount,
                "date": str(g.gifted_on),
                "deduction": g.tax_deduction_estimate,
                "status": g.status,
            }
            for g in gifts
        ],
        "lineage": lineage(),
    }


def retirement_payload(db: Session, user: m.User) -> dict:
    plan = db.query(m.Plan).first()
    options = db.query(m.InvestmentOption).filter(m.InvestmentOption.plan_id == plan.id).all() if plan else []
    fees = db.query(m.Fee).filter(m.Fee.plan_id == plan.id).all() if plan else []
    tests = db.query(m.ComplianceTest).filter(m.ComplianceTest.plan_id == plan.id).all() if plan else []
    participants = db.query(m.Participant).filter(m.Participant.plan_id == plan.id).all() if plan else []
    me = own_participant(db, user)
    if not me and user.role == "PARTICIPANT":
        me = None
    elif not me and user.role in {"CLIENT", "ADVISOR", "ADMIN", "SPONSOR"}:
        me = next((p for p in participants if p.email == user.email), None)
        if user.role in {"ADVISOR", "ADMIN", "SPONSOR"} and not me:
            me = next((p for p in participants if p.email == "alex.morgan@nexgile.demo"), participants[0] if participants else None)
            if user.role == "SPONSOR":
                me = None
    readiness = calc.retirement_readiness(me.income_projection if me else 0, 210000, 71.3)
    return with_currency({
        "sponsor": {
            "plan_name": plan.name if plan else "",
            "sponsor_name": plan.sponsor_name if plan else "",
            "plan_assets": plan.plan_assets if plan else 0,
            "participants": plan.participants if plan else 0,
            "participation_rate": plan.participation_rate if plan else 0,
            "avg_deferral_rate": plan.avg_deferral_rate if plan else 0,
            "employer_match": plan.employer_match if plan else "",
            "vesting": plan.vesting if plan else "",
            "plan_health": plan.plan_health if plan else "",
            "fees_bps": plan.fees_bps if plan else 0,
            "compliance_status": plan.compliance_status if plan else "",
            "lineup": [
                {"name": o.name, "ticker": o.ticker, "category": o.category, "er": o.expense_ratio, "ytd": o.ytd_return}
                for o in options
            ],
            "fees": [{"type": f.fee_type, "bps": f.amount_bps, "notes": f.notes} for f in fees],
            "tests": [{"name": t.name, "year": t.year, "result": t.result, "notes": t.notes} for t in tests],
        },
        "participant": {
            "name": me.name if me else user.full_name,
            "balance": me.balance if me else 0,
            "employee_ytd": me.employee_deferral_ytd if me else 0,
            "employer_ytd": me.employer_match_ytd if me else 0,
            "vested_pct": me.vested_pct if me else 0,
            "contribution_rate": me.contribution_rate if me else 0,
            "income_projection": me.income_projection if me else 0,
            "readiness": readiness,
            "beneficiaries": ["Jordan Morgan (primary)", "Cameron & Avery Morgan (contingent)"],
        },
        "lineage": lineage(),
    })


def documents_payload(db: Session, user: m.User) -> dict:
    hh = household_for_user(db, user)
    if not hh:
        return {"documents": [], "lineage": lineage()}
    docs = db.query(m.Document).filter(m.Document.household_id == hh.id).order_by(m.Document.uploaded_on.desc()).all()
    return {
        "documents": [
            {
                "id": d.id,
                "name": d.name,
                "category": d.category,
                "type": d.doc_type,
                "uploaded_on": str(d.uploaded_on),
                "version": d.version,
                "expiry_or_review": str(d.expiry_or_review) if d.expiry_or_review else None,
                "owner": d.owner,
                "status": d.status,
                "ai_classification": d.ai_classification,
            }
            for d in docs
        ],
        "lineage": lineage(),
    }


def classify_document(name: str) -> str:
    n = name.lower()
    if "1040" in n or "tax" in n or "k-1" in n:
        return "tax_return"
    if "trust" in n:
        return "estate_trust"
    if "will" in n:
        return "estate_will"
    if "401" in n or "spd" in n or "retirement" in n:
        return "retirement"
    if "statement" in n:
        return "statement"
    if "ips" in n or "policy" in n:
        return "ips"
    return "uncategorized"


def advisor_clients(db: Session, user: m.User) -> dict:
    ids = assigned_household_ids(db, user)
    q = db.query(m.Household)
    if user.role != "ADMIN":
        q = q.filter(m.Household.id.in_(ids or {-1}))
    households = q.all()
    rows = []
    for hh in households:
        accts = db.query(m.Account).filter(m.Account.household_id == hh.id).all()
        aum = round(sum(a.market_value or 0 for a in accts), 2)
        alerts = db.query(m.Alert).filter(m.Alert.household_id == hh.id).count()
        meeting = db.query(m.Meeting).filter(m.Meeting.household_id == hh.id).first()
        harvests = db.query(m.Harvest).filter(m.Harvest.household_id == hh.id).count()
        rows.append(
            {
                "id": hh.id,
                "client": hh.primary_client_name,
                "household": hh.name,
                "aum": aum or (4200000 if "Chen" in hh.name else 980000 if "Patel" in hh.name else aum),
                "risk": hh.risk_profile,
                "goals": db.query(m.Goal).filter(m.Goal.household_id == hh.id).count(),
                "tax_opportunity": harvests > 0,
                "next_meeting": str(meeting.scheduled_for) if meeting else ("2026-09-24" if "Chen" in hh.name else "2026-10-03"),
                "alerts": alerts,
            }
        )
    if not any(r["aum"] > 0 and "Chen" in r["household"] for r in rows):
        pass
    # Enrich non-Morgan demo households with realistic AUM for the workstation
    for r in rows:
        if r["household"] == "Chen Family" and r["aum"] == 0:
            r["aum"] = 6400000
            r["goals"] = 3
            r["tax_opportunity"] = True
            r["alerts"] = 2
        if r["household"] == "Patel Household" and r["aum"] == 0:
            r["aum"] = 1850000
            r["goals"] = 2
            r["tax_opportunity"] = False
            r["alerts"] = 1
    tasks = db.query(m.ActionItem).order_by(m.ActionItem.due_on).all()
    return {
        "clients": rows,
        "tasks": [
            {"id": t.id, "title": t.title, "owner": t.owner, "due": str(t.due_on), "status": t.status, "priority": t.priority}
            for t in tasks
        ],
        "lineage": lineage(),
    }


def client_360(db: Session, user: m.User, household_id: int) -> dict:
    if not can_access_household(db, user, household_id):
        raise AppError("FORBIDDEN", "You are not authorized to access this household.", 403)
    hh = db.query(m.Household).filter(m.Household.id == household_id).first()
    if not hh:
        raise AppError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    proxy_user = m.User(full_name=hh.primary_client_name, role="ADVISOR", household_id=hh.id, email="advisor")
    dash = dashboard(db, proxy_user)
    meeting = db.query(m.Meeting).filter(m.Meeting.household_id == hh.id).first()
    docs = documents_payload(db, proxy_user)
    msgs = db.query(m.Message).filter(m.Message.household_id == hh.id).all()
    tasks = db.query(m.ActionItem).filter(m.ActionItem.household_id == hh.id).all()
    return {
        "household": {"id": hh.id, "name": hh.name, "client": hh.primary_client_name, "risk": hh.risk_profile},
        "net_worth": dash["net_worth"],
        "accounts": accounts_payload(db, proxy_user)["accounts"],
        "portfolio": dash["portfolio"],
        "goals": dash["goals"],
        "tax": dash["tax_opportunities"],
        "documents": docs["documents"][:6],
        "messages": [{"id": m_.id, "subject": m_.subject, "sender": m_.sender, "date": str(m_.created_at)} for m_ in msgs],
        "tasks": [{"id": t.id, "title": t.title, "due": str(t.due_on), "status": t.status, "priority": t.priority} for t in tasks],
        "meeting_prep": {
            "title": meeting.title if meeting else "Next review",
            "when": str(meeting.scheduled_for) if meeting else None,
            "agenda": meeting.agenda if meeting else "Performance, tax, planning.",
            "talking_points": [
                "Technology overweight vs IPS 28% sleeve",
                "Approve INTC/NKE harvest; BND on wash-sale watch",
                "Healthcare directive refresh before Sep 30",
                "Tahoe down-payment remains on track at 65% funded",
            ],
        },
        "lineage": lineage(),
    }


def reports_payload(db: Session, user: m.User) -> dict:
    hh = household_for_user(db, user)
    if not hh:
        return {"reports": [], "preview_context": {}, "lineage": lineage()}
    reports = db.query(m.Report).filter(m.Report.household_id == hh.id).all()
    dash = dashboard(db, user)
    return {
        "reports": [
            {
                "id": r.id,
                "name": r.name,
                "type": r.report_type,
                "period": r.period,
                "generated_on": str(r.generated_on),
                "status": r.status,
                "summary": r.summary,
            }
            for r in reports
        ],
        "preview_context": {
            "household": hh.name,
            "client": hh.primary_client_name,
            "net_worth": dash["net_worth"]["total"],
            "invested": dash["portfolio"]["invested_assets"],
            "ytd": dash["portfolio"]["ytd_return"],
        },
        "lineage": lineage(),
    }


def report_preview(db: Session, user: m.User, report_id: int) -> dict:
    hh = household_for_user(db, user)
    if not hh:
        raise AppError("FORBIDDEN", "No authorized household is available for this account.", 403)
    r = db.query(m.Report).filter(m.Report.id == report_id, m.Report.household_id == hh.id).first()
    if not r:
        raise AppError("RESOURCE_NOT_FOUND", "The requested resource was not found.", 404)
    dash = dashboard(db, user)
    return with_currency({
        "report": {
            "id": r.id if r else report_id,
            "name": r.name if r else "Household Report",
            "type": r.report_type if r else "household_wealth",
            "period": r.period if r else "September 2026",
            "generated_on": str(r.generated_on) if r else AS_OF,
            "summary": r.summary if r else "",
        },
        "household": hh.name,
        "prepared_for": hh.primary_client_name,
        "prepared_by": "Sarah Wilson, CFP® CFA",
        "as_of": AS_OF,
        "disclaimer": "For discussion with your Nexgile advisor. Not tax, legal, or investment advice.",
        "sections": [
            {"heading": "Net worth", "body": f"Total net worth {format_inr(dash['net_worth']['total'])} as of {AS_OF}."},
            {"heading": "Invested assets", "body": f"{format_inr(dash['portfolio']['invested_assets'])} with YTD return {dash['portfolio']['ytd_return']}% vs 11.4% 60/40 blend."},
            {"heading": "Goals", "body": "; ".join(f"{g['category']} {g['pct']}% funded" for g in dash["goals"])},
            {"heading": "Tax", "body": f"Harvest candidates INTC, NKE, BND. Gains budget {format_inr((hh.capital_gains_budget_limit or 0) - (hh.capital_gains_budget_used or 0))} remaining."},
        ],
        "lineage": lineage(),
    })


def messages_payload(db: Session, user: m.User) -> dict:
    hh = household_for_user(db, user)
    if not hh:
        return {"messages": [], "lineage": lineage()}
    msgs = db.query(m.Message).filter(m.Message.household_id == hh.id).order_by(m.Message.created_at.desc()).all()
    return {
        "messages": [
            {
                "id": x.id,
                "sender": x.sender,
                "role": x.sender_role,
                "subject": x.subject,
                "body": x.body,
                "created_at": x.created_at.isoformat() if x.created_at else None,
                "read": x.read,
                "thread_id": x.thread_id,
            }
            for x in msgs
        ],
        "lineage": lineage(),
    }


def notifications_payload(db: Session, user: m.User) -> dict:
    hh = household_for_user(db, user)
    q = db.query(m.Alert)
    if hh:
        q = q.filter((m.Alert.household_id == hh.id) | (m.Alert.household_id.is_(None)))
    alerts = q.order_by(m.Alert.created_at.desc()).all()
    return {
        "notifications": [
            {
                "id": a.id,
                "title": a.title,
                "body": a.body,
                "severity": a.severity,
                "category": a.category,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "read": a.read,
            }
            for a in alerts
        ],
        "unread": sum(1 for a in alerts if not a.read),
        "lineage": lineage(),
    }


def search_payload(db: Session, user: m.User, q: str) -> dict:
    qn = (q or "").strip().lower()
    hh = household_for_user(db, user)
    cats = {"clients": [], "accounts": [], "holdings": [], "goals": [], "documents": [], "reports": [], "messages": []}
    if not qn:
        return {"query": q, "results": cats, "lineage": lineage()}
    for h in db.query(m.Household).filter(m.Household.id.in_(assigned_household_ids(db, user) or {-1})).all():
        if qn in (h.name or "").lower() or qn in (h.primary_client_name or "").lower():
            cats["clients"].append({"id": h.id, "label": h.primary_client_name, "sub": h.name})
    if hh:
        for a in db.query(m.Account).filter(m.Account.household_id == hh.id).all():
            if qn in a.name.lower() or qn in (a.account_type or ""):
                cats["accounts"].append({"id": a.id, "label": a.name, "sub": a.account_type})
        for hold in _holdings(db, hh.id):
            if qn in (hold.symbol or "").lower() or qn in (hold.name or "").lower():
                cats["holdings"].append({"id": hold.id, "label": f"{hold.symbol} — {hold.name}", "sub": hold.asset_class})
        for g in db.query(m.Goal).filter(m.Goal.household_id == hh.id).all():
            if qn in g.name.lower() or qn in (g.category or "").lower():
                cats["goals"].append({"id": g.id, "label": g.name, "sub": g.category})
        for d in db.query(m.Document).filter(m.Document.household_id == hh.id).all():
            if qn in d.name.lower() or qn in (d.category or "").lower():
                cats["documents"].append({"id": d.id, "label": d.name, "sub": d.category})
        for r in db.query(m.Report).filter(m.Report.household_id == hh.id).all():
            if qn in r.name.lower() or qn in (r.report_type or "").lower():
                cats["reports"].append({"id": r.id, "label": r.name, "sub": r.period})
        for msg in db.query(m.Message).filter(m.Message.household_id == hh.id).all():
            if qn in (msg.subject or "").lower() or qn in (msg.body or "").lower():
                cats["messages"].append({"id": msg.id, "label": msg.subject, "sub": msg.sender})
    return {"query": q, "results": cats, "lineage": lineage()}
