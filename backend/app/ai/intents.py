"""Lightweight deterministic intent classifier. Swap for an LLM classifier later."""
from __future__ import annotations

INTENTS = (
    "PORTFOLIO_PERFORMANCE",
    "PORTFOLIO_ALLOCATION",
    "GOAL_PROGRESS",
    "RETIREMENT_READINESS",
    "TAX_OPPORTUNITY",
    "DOCUMENT_QUERY",
    "ESTATE_STATUS",
    "PHILANTHROPY",
    "ACCOUNT_SUMMARY",
    "RECENT_ACTIVITY",
    "GENERAL_WEALTH_QUERY",
    "FORBIDDEN_ACTION",
    "CROSS_HOUSEHOLD_PROBE",
)

_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("FORBIDDEN_ACTION", ("execute trade", "place trade", "approve the distribution", "change beneficiary", "wire funds", "sell everything")),
    ("PORTFOLIO_PERFORMANCE", ("perform", "return", "today", "ytd", "gain", "how is my portfolio")),
    ("PORTFOLIO_ALLOCATION", ("alloc", "overweight", "underweight", "sector", "rebalance", "equity")),
    ("TAX_OPPORTUNITY", ("tax", "harvest", "tlh", "roth", "wash", "rmd", "gain budget")),
    ("RETIREMENT_READINESS", ("retire", "on track", "readiness", "replacement income")),
    ("GOAL_PROGRESS", ("goal", "education", "legacy", "tahoe", "funded")),
    ("DOCUMENT_QUERY", ("document", "vault", "expir", "attention", "will", "directive", "ips")),
    ("ESTATE_STATUS", ("estate", "trust", "beneficiary", "poa", "probate")),
    ("PHILANTHROPY", ("philanthrop", "charit", "daf", "qcd", "gift", "giving")),
    ("ACCOUNT_SUMMARY", ("account", "ira", "401", "brokerage", "cash reserve")),
    ("RECENT_ACTIVITY", ("activity", "transaction", "contribution", "what changed", "why did")),
]


def classify_intent(message: str) -> str:
    q = (message or "").lower()
    for intent, keys in _RULES:
        if any(k in q for k in keys):
            return intent
    return "GENERAL_WEALTH_QUERY"
