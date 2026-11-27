"""Groq chat provider. Called only from the FastAPI AI layer. Never from React."""
from __future__ import annotations

import json
import logging
import re
import time

import httpx

from app.ai.guardrails import DISCLAIMER
from app.ai.providers.base import ProviderError, USER_UNAVAILABLE
from app.core.config import get_settings
from app.core.currency import currency_meta

log = logging.getLogger("wealthagent.ai.groq")

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.I)


def compact_authorized_payload(context: dict, documents: list[dict]) -> dict:
    """Verified calculation results only. Authorization already applied by the orchestrator."""
    portfolio = context.get("portfolio") or {}
    goals = context.get("goals") or {}
    tax = context.get("tax") or {}
    dashboard = context.get("dashboard") or {}
    retirement = context.get("retirement") or {}
    return {
        "household": context.get("household"),
        "intent": context.get("intent"),
        "as_of": get_settings().as_of_date,
        **currency_meta(),
        "portfolio_summary": portfolio.get("summary"),
        "benchmark": portfolio.get("benchmark"),
        "goals": goals.get("goals") if isinstance(goals, dict) else goals,
        "monte_carlo": goals.get("monte_carlo") if isinstance(goals, dict) else None,
        "retirement": retirement,
        "tax": {
            "estimated_liability": tax.get("estimated_liability"),
            "capital_gains_budget": tax.get("capital_gains_budget"),
            "harvests": tax.get("harvests"),
        }
        if tax
        else None,
        "accounts": (context.get("accounts") or {}).get("accounts"),
        "estate": context.get("estate"),
        "philanthropy": context.get("philanthropy"),
        "documents": (context.get("documents") or {}).get("documents"),
        "dashboard": {
            "net_worth": dashboard.get("net_worth"),
            "portfolio": dashboard.get("portfolio"),
        },
        "rag": [{"name": d.get("name"), "category": d.get("category"), "text": d.get("text")} for d in documents],
        "instruction": (
            "Figures are verified by the calculation engine and are INR. "
            "Cite amounts with ₹ and Indian grouping (en-IN). Never call these figures US dollars. "
            "Percentages remain percentages. Explain them. Do not recompute or invent values."
        ),
    }


class GroqProvider:
    name = "groq"

    def __init__(self):
        settings = get_settings()
        self.model = settings.groq_model
        self.api_key = settings.groq_api_key
        self.base = (settings.groq_api_base or "https://api.groq.com/openai/v1").rstrip("/")
        self.timeout = settings.groq_timeout_seconds
        self.retries = settings.groq_retries

    def generate(self, *, system_prompt: str, user_message: str, context: dict, documents: list[dict]) -> dict:
        if not self.api_key:
            raise ProviderError("missing_key")
        compact = compact_authorized_payload(context, documents)
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{system_prompt}\n\n"
                        "Explain the authorized CONTEXT. Monetary figures are INR — use ₹ and Indian grouping. "
                        "Do not recalculate financial figures. "
                        "Do not mention other households. Do not claim to execute trades. "
                        'Respond as JSON: {"answer":"...","assumptions":[],"limitations":[]}.'
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "CONTEXT (authorized book-of-record and calculation-engine results only):\n"
                        f"{json.dumps(compact, default=str)[:12000]}\n\nQUESTION:\n{user_message}"
                    ),
                },
            ],
        }
        data = self._post(payload)
        try:
            message = data["choices"][0]["message"]
            content = message.get("content") or message.get("reasoning") or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("malformed_response") from exc
        parsed = _parse_model_content(content)
        answer = (parsed.get("answer") or "").strip()
        if not answer:
            raise ProviderError("malformed_response")
        usage = data.get("usage") or {}
        return {
            "answer": answer,
            "model": data.get("model") or self.model,
            "token_usage": {
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
            },
            "sources": ["Authorized household context", "Calculation engine", "Document RAG (permission filtered)"],
            "assumptions": parsed.get("assumptions")
            or ["Explanation uses verified calculation-engine results supplied in CONTEXT."],
            "limitations": parsed.get("limitations") or ["Not financial advice. Advisor review required."],
            "disclaimer": DISCLAIMER,
        }

    def _post(self, payload: dict) -> dict:
        last_error: ProviderError | None = None
        for attempt in range(self.retries + 1):
            try:
                resp = httpx.post(
                    f"{self.base}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout,
                )
            except httpx.TimeoutException:
                last_error = ProviderError("timeout")
                log.warning("groq_timeout attempt=%s", attempt + 1)
                _backoff(attempt)
                continue
            except httpx.RequestError as exc:
                last_error = ProviderError("unavailable")
                log.warning("groq_request_error attempt=%s err=%s", attempt + 1, type(exc).__name__)
                _backoff(attempt)
                continue

            if resp.status_code in {429, 500, 502, 503}:
                last_error = ProviderError("rate_limit" if resp.status_code == 429 else "unavailable")
                log.warning("groq_transient status=%s attempt=%s", resp.status_code, attempt + 1)
                _backoff(attempt)
                continue
            if resp.status_code == 404:
                log.error("groq_http_error status=404 model=%s", self.model)
                raise ProviderError("model_unavailable")
            if resp.status_code in {401, 403}:
                log.error("groq_auth_rejected status=%s", resp.status_code)
                raise ProviderError("invalid_key")
            if resp.status_code >= 400:
                log.error("groq_http_error status=%s", resp.status_code)
                raise ProviderError("unavailable")
            try:
                return resp.json()
            except ValueError as exc:
                raise ProviderError("malformed_response") from exc
        raise last_error or ProviderError("unavailable")


def _backoff(attempt: int) -> None:
    time.sleep(min(1.5 * (2 ** attempt), 8.0))


def _parse_model_content(content: str) -> dict:
    text = _FENCE.sub("", (content or "").strip())
    try:
        data = json.loads(text)
        if isinstance(data, dict) and data.get("answer"):
            return data
    except json.JSONDecodeError:
        pass
    return {"answer": content or USER_UNAVAILABLE}
