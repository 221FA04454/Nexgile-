"""Deterministic provider: answers from authorized PostgreSQL context only."""
from __future__ import annotations

from app.core.config import get_settings
from app.core.currency import format_inr
from app.ai.guardrails import DISCLAIMER


class DeterministicProvider:
    name = "deterministic"
    model = "deterministic-v1"

    def generate(self, *, system_prompt: str, user_message: str, context: dict, documents: list[dict]) -> dict:
        settings = get_settings()
        as_of = settings.as_of_date
        hh = (context.get("household") or {}) or {}
        hh_name = hh.get("name") or "your household"
        intent = context.get("intent") or "GENERAL_WEALTH_QUERY"
        sources = ["Household book of record", f"As-of {as_of}", "Internal calculation engine"]
        assumptions = [
            f"Mark-to-market prices as of {as_of}",
            "Figures come from authorized PostgreSQL records and the calculation engine.",
        ]
        limitations = [
            "Informational only — not financial, tax, or legal advice.",
            "Scenarios and previews do not modify the book of record.",
        ]
        answer = _answer(intent, context, documents, hh_name, as_of, sources)
        return {
            "answer": answer,
            "model": self.model,
            "token_usage": {},
            "sources": sources,
            "assumptions": assumptions,
            "limitations": limitations,
            "disclaimer": DISCLAIMER,
        }


def _fmt(n) -> str:
    return format_inr(n)


def _answer(intent: str, context: dict, documents: list[dict], hh_name: str, as_of: str, sources: list) -> str:
    if intent in {"PORTFOLIO_PERFORMANCE", "RECENT_ACTIVITY"} and context.get("portfolio"):
        s = context["portfolio"]["summary"]
        bench = context["portfolio"].get("benchmark") or {}
        return (
            f"As of {as_of}, {hh_name} invested assets are {_fmt(s.get('total_market_value'))}. "
            f"Today's mark-to-market move is {_fmt(s.get('day_change'))} ({float(s.get('day_change_pct') or 0):+0.2f}%). "
            f"Year-to-date return is approximately {s.get('ytd_return_pct')}%, "
            f"versus {bench.get('ytd')}% for {bench.get('name') or 'the benchmark'}. "
            f"Unrealized gain/loss is {_fmt(s.get('unrealized_gain_loss'))}. "
            "This is a book-of-record mark, not a cash flow."
        )
    if intent == "PORTFOLIO_ALLOCATION" and context.get("portfolio"):
        alloc = context["portfolio"]["summary"].get("allocation") or []
        parts = ", ".join(f"{a.get('name')} {a.get('pct')}%" for a in alloc[:6])
        return (
            f"{hh_name} allocation as of {as_of}: {parts or 'not available'}. "
            "A rebalance preview can be generated without changing the book of record; trades require approval."
        )
    if intent == "TAX_OPPORTUNITY" and context.get("tax"):
        tax = context["tax"]
        harvests = tax.get("harvests") or []
        names = ", ".join(h.get("symbol") for h in harvests) or "none identified"
        benefit = sum(h.get("potential_tax_benefit") or 0 for h in harvests)
        sources.append("Tax lot file")
        return (
            f"Tax opportunities for {hh_name} as of {as_of}: estimated overlay {_fmt(tax.get('estimated_liability'))}. "
            f"Capital-gains budget remaining {_fmt((tax.get('capital_gains_budget') or {}).get('remaining'))}. "
            f"Harvest candidates: {names}. Combined potential federal benefit about {_fmt(benefit)}. "
            "This is not a guaranteed tax saving. Any harvest must go through the existing approval workflow — I cannot execute it."
        )
    if intent in {"RETIREMENT_READINESS", "GOAL_PROGRESS"} and context.get("goals"):
        goals = context["goals"].get("goals") or []
        if not goals:
            return f"No goals are on file for {hh_name} as of {as_of}."
        ret = next((g for g in goals if (g.get("category") or "").lower() == "retirement"), goals[0])
        mc = context["goals"].get("monte_carlo") or {}
        sources.append("Goals ledger + calculation engine")
        return (
            f"Goal '{ret.get('name')}' is {ret.get('pct')}% funded "
            f"({_fmt(ret.get('current'))} of {_fmt(ret.get('target'))}), target {ret.get('target_date')}. "
            f"Base-case probability from the planning engine is {(ret.get('probability') or 0)*100:.0f}%. "
            f"Monte Carlo median {_fmt(mc.get('p50'))} with {mc.get('success_rate')}% of paths at/above target. "
            "This is not a guarantee the household will meet the goal."
        )
    if intent == "DOCUMENT_QUERY":
        docs = (context.get("documents") or {}).get("documents") or []
        due = [d for d in docs if d.get("status") in {"review_due", "expiring"}]
        listing = "; ".join(f"{d.get('name')} ({d.get('status')})" for d in due) or "none flagged in metadata"
        if documents:
            rag_names = "; ".join(d.get("name") for d in documents[:4])
            sources.append("Document vault RAG")
            listing = listing + f". Retrieved vault passages: {rag_names}"
        return f"Document items needing attention for {hh_name}: {listing}."
    if intent == "ESTATE_STATUS" and context.get("estate"):
        e = context["estate"]
        return (
            f"Estate readiness for {hh_name} is {e.get('readiness_score')}. "
            f"Will {e.get('documents', {}).get('will')}, trust {e.get('documents', {}).get('trust')}. "
            "Beneficiary or document changes require the existing workflow."
        )
    if intent == "PHILANTHROPY" and context.get("philanthropy"):
        p = context["philanthropy"]
        daf = (p.get("daf") or {}) if isinstance(p.get("daf"), dict) else {}
        return (
            f"Philanthropy for {hh_name}: DAF balance {_fmt(daf.get('balance') or p.get('daf_balance'))}. "
            "Grants are recorded in the book; I cannot initiate a gift."
        )
    if intent == "ACCOUNT_SUMMARY" and context.get("accounts"):
        accts = context["accounts"].get("accounts") or []
        names = ", ".join(f"{a.get('name')} {_fmt(a.get('market_value'))}" for a in accts[:8])
        return f"{hh_name} accounts as of {as_of}: {names or 'none'}."
    dash = context.get("dashboard") or {}
    nw = (dash.get("net_worth") or {}).get("total")
    invested = (dash.get("portfolio") or {}).get("invested_assets")
    return (
        f"{hh_name} book as of {as_of}: net worth {_fmt(nw)}, invested assets {_fmt(invested)}. "
        "Ask about performance, tax, retirement, documents, or accounts."
    )
