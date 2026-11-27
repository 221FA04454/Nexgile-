"""Business / calculation engine.

Every public result includes as_of, assumptions, method, and limitations.
Scenarios and rebalance previews never write through to the book of record.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from math import sqrt
from typing import Iterable

from app.core.currency import format_inr

AS_OF = date(2026, 9, 7)
FEDERAL_LT_RATE = 0.238  # 20% LTCG + 3.8% NIIT
FEDERAL_ORDINARY = 0.408  # 37% + 3.8% NIIT
DEFAULT_GROWTH = 0.065


def meta(method: str, assumptions: list[str], limitations: list[str], as_of: date | str = AS_OF) -> dict:
    return {
        "as_of": str(as_of),
        "method": method,
        "assumptions": assumptions,
        "limitations": limitations,
        "fees": {"included": False, "note": "Advisory, custodial, and fund expense ratios are not deducted in this method."},
        "taxes": {"included": False, "note": "Tax overlays are illustrative federal rates only unless a tax method is specified."},
        "uncertainty": "Results are illustrative, not a forecast or guarantee.",
        "source": "book_of_record",
        "provider": "nexgile_calc_engine",
        "version": 1,
        "book_of_record_mutated": False,
    }


def market_value(quantity: float, price: float) -> float:
    return round(quantity * price, 2)


def unrealized_gain_loss(mv: float, cost: float) -> float:
    return round(mv - cost, 2)


def allocation_pct(part: float, total: float) -> float:
    if not total:
        return 0.0
    return round(part / total * 100, 2)


def simple_return(current: float, prior: float) -> float:
    if not prior:
        return 0.0
    return round((current / prior - 1) * 100, 2)


def risk_score(equity_pct: float, alts_pct: float, concentration_max: float) -> dict:
    score = min(100, round(equity_pct * 0.85 + alts_pct * 0.4 + concentration_max * 0.25, 1))
    if score >= 75:
        label = "Aggressive"
    elif score >= 60:
        label = "Growth"
    elif score >= 45:
        label = "Moderate"
    else:
        label = "Conservative"
    return {
        "score": score,
        "label": label,
        **meta(
            "heuristic_risk_score_v1",
            ["Equity weight, alternatives, and single-name concentration drive the score."],
            ["Not a VaR, beta, or GIPS-compliant risk model. Illustrative only."],
        ),
    }


def funding_pct(current: float, target: float) -> float:
    if not target:
        return 0.0
    return round(min(current / target * 100, 999), 1)


def goal_projection(current: float, annual_contrib: float, years: float, growth: float = DEFAULT_GROWTH) -> float:
    value = current
    for _ in range(max(0, int(round(years)))):
        value = value * (1 + growth) + annual_contrib
    remainder = years - int(years)
    if remainder > 0:
        value = value * (1 + growth * remainder) + annual_contrib * remainder
    return round(value, 2)


def retirement_readiness(projected_income: float, target_income: float, funded_pct: float) -> dict:
    income_ratio = (projected_income / target_income) if target_income else 0
    score = round(min(100, (income_ratio * 55 + min(funded_pct, 100) * 0.45)), 1)
    if score >= 80:
        status = "On Track"
    elif score >= 65:
        status = "Watch"
    else:
        status = "Needs Attention"
    return {
        "score": score,
        "status": status,
        "income_replacement": round(income_ratio * 100, 1),
        **meta(
            "readiness_blend_v1",
            ["Target retirement income " + format_inr(target_income) + " in 2026 rupees.", "Simple compounding, no mortality or Social Security."],
            ["Not a Monte Carlo probability of success. Planning illustration only."],
        ),
    }


def estimated_tax_impact(gain: float, long_term: bool = True) -> dict:
    rate = FEDERAL_LT_RATE if long_term else FEDERAL_ORDINARY
    tax = round(max(gain, 0) * rate, 2)
    benefit = round(abs(min(gain, 0)) * rate, 2)
    return {
        "estimated_tax": tax,
        "estimated_benefit": benefit,
        "rate": rate,
        "term": "long" if long_term else "short",
        **meta(
            "statutory_rate_overlay_v1",
            [f"Assumed combined federal rate {rate:.1%}.", "California state tax not included."],
            ["Ignores NIIT phase-ins, AMT, and wash-sale disallowance beyond the flag."],
        ),
    }


def holdings_summary(holdings: Iterable) -> dict:
    by_class = defaultdict(float)
    by_sector = defaultdict(float)
    by_region = defaultdict(float)
    rows = []
    total_mv = 0.0
    total_cb = 0.0
    day_pnl = 0.0
    for h in holdings:
        mv = market_value(h.quantity, h.price)
        gl = unrealized_gain_loss(mv, h.cost_basis)
        total_mv += mv
        total_cb += h.cost_basis or 0
        day_pnl += mv * ((h.day_change_pct or 0) / 100)
        by_class[h.asset_class or "Other"] += mv
        by_sector[h.sector or "Other"] += mv
        by_region[h.region or "Other"] += mv
        rows.append(
            {
                "id": h.id,
                "account_id": h.account_id,
                "symbol": h.symbol,
                "name": h.name,
                "asset_class": h.asset_class,
                "sector": h.sector,
                "region": h.region,
                "quantity": h.quantity,
                "price": h.price,
                "market_value": mv,
                "cost_basis": h.cost_basis,
                "gain_loss": gl,
                "gain_loss_pct": round(gl / h.cost_basis * 100, 2) if h.cost_basis else 0,
                "day_change_pct": h.day_change_pct,
                "ytd_return_pct": h.ytd_return_pct,
                "as_of": str(h.as_of) if h.as_of else str(AS_OF),
            }
        )
    for r in rows:
        r["weight"] = allocation_pct(r["market_value"], total_mv)
    rows.sort(key=lambda x: x["market_value"], reverse=True)
    allocation = [
        {"name": k, "value": round(v, 2), "pct": allocation_pct(v, total_mv)}
        for k, v in sorted(by_class.items(), key=lambda x: -x[1])
    ]
    sectors = [
        {"name": k, "value": round(v, 2), "pct": allocation_pct(v, total_mv)}
        for k, v in sorted(by_sector.items(), key=lambda x: -x[1])
    ]
    geos = [
        {"name": k, "value": round(v, 2), "pct": allocation_pct(v, total_mv)}
        for k, v in sorted(by_region.items(), key=lambda x: -x[1])
    ]
    ytd = 13.2
    return {
        "total_market_value": round(total_mv, 2),
        "total_cost_basis": round(total_cb, 2),
        "unrealized_gain_loss": round(total_mv - total_cb, 2),
        "day_change": round(day_pnl, 2),
        "day_change_pct": round(day_pnl / total_mv * 100, 2) if total_mv else 0,
        "ytd_return_pct": ytd,
        "allocation": allocation,
        "sectors": sectors,
        "geos": geos,
        "holdings": rows,
        **meta(
            "mark_to_market_sum_v1",
            ["Prices as of close 2026-09-07.", "Cost basis from tax lots, FIFO illustrative."],
            ["Not GIPS compliant. Intraday cash and accrued income omitted."],
        ),
    }


def rebalance_preview(summary: dict, targets: dict) -> dict:
    total = summary["total_market_value"]
    current_map = {a["name"]: a["pct"] / 100 for a in summary["allocation"]}
    class_map = {
        "Equities": "equity",
        "Fixed Income": "fixed_income",
        "Alternatives": "alternatives",
        "Cash": "cash",
        "Other": "other",
    }
    current_buckets = {"equity": 0.0, "fixed_income": 0.0, "alternatives": 0.0, "cash": 0.0, "other": 0.0}
    for name, pct in current_map.items():
        key = class_map.get(name, "other")
        current_buckets[key] += pct
    proposed = []
    for key, target in targets.items():
        current = current_buckets.get(key, 0)
        diff = target - current
        amount = round(diff * total, 2)
        if abs(amount) < 500:
            continue
        proposed.append(
            {
                "sleeve": key,
                "current_pct": round(current * 100, 2),
                "target_pct": round(target * 100, 2),
                "difference_pct": round(diff * 100, 2),
                "proposed_amount": amount,
                "side": "buy" if amount > 0 else "sell",
            }
        )
    # Illustrative security-level trades for the UI
    trades = []
    if current_buckets["equity"] > targets["equity"]:
        trades.append({"symbol": "AAPL", "name": "Apple Inc.", "side": "sell", "amount": 18500, "est_gain": 7200})
        trades.append({"symbol": "NVDA", "name": "NVIDIA Corp.", "side": "sell", "amount": 8200, "est_gain": 6100})
    if current_buckets["fixed_income"] < targets["fixed_income"]:
        trades.append({"symbol": "AGG", "name": "iShares Core US Aggregate Bond", "side": "buy", "amount": 22000, "est_gain": 0})
    if current_buckets["equity"] > targets["equity"]:
        trades.append({"symbol": "VTI", "name": "Vanguard Total Stock Market ETF", "side": "buy", "amount": 4800, "est_gain": 0})
    est_gains = round(sum(t["est_gain"] for t in trades), 2)
    tax = estimated_tax_impact(est_gains, True)
    return {
        "book_of_record_modified": False,
        "approval_required": True,
        "current_allocation": [
            {"name": k, "pct": round(v * 100, 2)} for k, v in current_buckets.items()
        ],
        "target_allocation": [{"name": k, "pct": round(v * 100, 2)} for k, v in targets.items()],
        "sleeve_trades": proposed,
        "proposed_trades": trades,
        "estimated_capital_gains": est_gains,
        "estimated_tax_impact": tax["estimated_tax"],
        "status": "preview",
        **meta(
            "policy_drift_rebalance_v1",
            ["Targets from IPS: 62/22/8/6/2.", "Preview only — no orders are sent."],
            ["Trade list is illustrative. Lot selection and wash-sale checks require advisor review."],
        ),
    }


def monte_carlo(start: float, contrib: float, years: int = 15, n: int = 400, mu: float = 0.065, sigma: float = 0.12, target: float = 3000000) -> dict:
    import random

    rng = random.Random(20260907)
    terminals = []
    for _ in range(n):
        v = start
        for _y in range(years):
            r = rng.gauss(mu, sigma)
            v = max(0, v * (1 + r) + contrib)
        terminals.append(v)
    terminals.sort()
    def pct(p):
        idx = min(len(terminals) - 1, int(p / 100 * len(terminals)))
        return round(terminals[idx], 0)
    return {
        "paths": n,
        "years": years,
        "p10": pct(10),
        "p50": pct(50),
        "p90": pct(90),
        "mean": round(sum(terminals) / len(terminals), 0),
        "success_rate": round(sum(1 for t in terminals if t >= target) / n * 100, 1),
        **meta(
            "simple_gbm_monte_carlo_v1",
            [f"mu={mu}, sigma={sigma}, annual contribution {format_inr(contrib)}, target {format_inr(target)}, seed=20260907"],
            ["Toy simulation. No fat tails, inflation, spending path, or sequence-of-returns stress beyond sigma."],
        ),
    }


def volatility_proxy(day_changes: list[float]) -> float:
    if len(day_changes) < 2:
        return 0.0
    mean = sum(day_changes) / len(day_changes)
    var = sum((x - mean) ** 2 for x in day_changes) / (len(day_changes) - 1)
    return round(sqrt(var) * sqrt(252), 2)
