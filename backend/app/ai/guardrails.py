"""Financial AI guardrails. Applied before and after provider calls."""
from __future__ import annotations

import re

DISCLAIMER = (
    "Nexgile WealthAgent is an informational assistant that uses household book-of-record data. "
    "It does not provide financial, tax, or legal advice. Recommendations require advisor review "
    "before any trade, distribution, or beneficiary change."
)

FORBIDDEN_ACTION_PHRASES = (
    "i have executed",
    "i executed the trade",
    "trade has been placed",
    "i have placed the trade",
    "i approved the distribution",
    "beneficiary has been updated",
    "i have modified the book",
    "tax savings are guaranteed",
)

_GUARANTEE = re.compile(r"\b(guarantee[ds]?|certainly will|cannot lose)\b", re.I)
_NOT_A_GUARANTEE = re.compile(r"\bnot (a )?guarantee|\bnot guaranteed\b", re.I)


def is_forbidden_request(message: str) -> bool:
    q = (message or "").lower()
    verbs = ("execute", "place the trade", "wire", "approve distribution", "change my beneficiary", "update the book")
    return any(v in q for v in verbs) and any(n in q for n in ("trade", "beneficiary", "distribution", "wire", "account"))


def sanitize_answer(text: str) -> str:
    out = text or ""
    lowered = out.lower()
    if any(p in lowered for p in FORBIDDEN_ACTION_PHRASES):
        return (
            "I cannot execute trades, change the book of record, or promise outcomes. "
            "Use the existing approval workflow for any recommended action."
        )
    if _GUARANTEE.search(out) and not _NOT_A_GUARANTEE.search(out):
        out += " Figures are illustrative only and are not a guarantee."
    return out


def unavailable_payload(as_of: str, prompt_version: str, request_id: str = "") -> dict:
    answer = "AI service is temporarily unavailable. Please try again."
    if request_id:
        answer = f"{answer} Reference {request_id}."
    return {
        "reply": answer,
        "answer": answer,
        "sources": [],
        "as_of": as_of,
        "assumptions": [],
        "limitations": ["The generation provider did not return a usable response."],
        "advisor_review_required": True,
        "advisor_review_indicator": "Advisor review required before acting.",
        "disclaimer": DISCLAIMER,
        "refused": False,
        "prompt_version": prompt_version,
        "provider": "unavailable",
    }


def refusal_payload(reason: str, as_of: str, prompt_version: str) -> dict:
    answer = (
        f"{reason} I can only discuss the household book of record you are authorized to access. "
        "I do not retrieve another client's accounts, documents, or goals."
    )
    return {
        "reply": answer,
        "answer": answer,
        "sources": [],
        "as_of": as_of,
        "assumptions": [],
        "limitations": ["Authorization is enforced before retrieval. The model never receives unauthorized context."],
        "advisor_review_required": True,
        "advisor_review_indicator": "Advisor review required before acting.",
        "disclaimer": DISCLAIMER,
        "refused": True,
        "prompt_version": prompt_version,
    }
