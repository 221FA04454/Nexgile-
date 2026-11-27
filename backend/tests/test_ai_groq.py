import json

from app.ai.providers.base import ProviderError
from app.ai.providers.groq import GroqProvider, compact_authorized_payload
from app.ai.providers import resolve_provider
from app.core.config import get_settings
from tests.conftest import auth_header, make_client


def test_groq_selected_when_key_present(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    get_settings.cache_clear()
    provider = resolve_provider()
    assert isinstance(provider, GroqProvider)
    assert provider.model == "llama-3.3-70b-versatile"
    get_settings.cache_clear()


def test_compact_payload_is_authorized_context_only():
    ctx = {
        "household": {"id": 1, "name": "Morgan Family"},
        "intent": "PORTFOLIO_PERFORMANCE",
        "portfolio": {"summary": {"total_market_value": 2810334.3}},
        "tax": {"harvests": [{"symbol": "INTC"}]},
    }
    docs = [{"name": "IPS", "category": "Investment", "text": "equity 62%", "household_id": 1}]
    payload = compact_authorized_payload(ctx, docs)
    blob = json.dumps(payload)
    assert "Morgan Family" in blob
    assert "2810334.3" in blob
    assert payload["currency"] == "INR"
    assert "US dollars" in payload["instruction"]
    assert "GROQ_API_KEY" not in blob


def test_groq_generate_parses_json_answer(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    get_settings.cache_clear()

    class FakeResp:
        status_code = 200

        def json(self):
            return {
                "model": "llama-3.3-70b-versatile",
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "answer": "Morgan Family invested assets are ₹28,10,334 as of the book.",
                                    "assumptions": ["Calculation engine figures"],
                                    "limitations": ["Not advice"],
                                }
                            )
                        }
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 22},
            }

    monkeypatch.setattr("app.ai.providers.groq.httpx.post", lambda *a, **k: FakeResp())
    out = GroqProvider().generate(
        system_prompt="sys",
        user_message="How is my portfolio performing?",
        context={"household": {"name": "Morgan Family"}, "intent": "PORTFOLIO_PERFORMANCE", "portfolio": {"summary": {"total_market_value": 2810334.3}}},
        documents=[],
    )
    assert "28,10,334" in out["answer"] or "2810334" in out["answer"].replace(",", "")
    assert out["model"] == "llama-3.3-70b-versatile"
    assert out["token_usage"]["prompt_tokens"] == 11
    get_settings.cache_clear()


def test_groq_retries_then_succeeds(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    get_settings.cache_clear()
    calls = {"n": 0}

    class Transient:
        status_code = 429

        def json(self):
            return {}

    class Ok:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Chen data must not appear. Morgan YTD is 13.2%."}}], "usage": {}}

    def fake_post(*a, **k):
        calls["n"] += 1
        return Transient() if calls["n"] == 1 else Ok()

    monkeypatch.setattr("app.ai.providers.groq.httpx.post", fake_post)
    monkeypatch.setattr("app.ai.providers.groq._backoff", lambda *_: None)
    out = GroqProvider().generate(
        system_prompt="sys",
        user_message="q",
        context={"household": {"name": "Morgan Family"}},
        documents=[],
    )
    assert calls["n"] == 2
    assert "13.2%" in out["answer"]
    get_settings.cache_clear()


def test_groq_invalid_key_raises(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    get_settings.cache_clear()

    class Unauthorized:
        status_code = 401

        def json(self):
            return {"error": "invalid"}

    monkeypatch.setattr("app.ai.providers.groq.httpx.post", lambda *a, **k: Unauthorized())
    try:
        GroqProvider().generate(system_prompt="s", user_message="q", context={}, documents=[])
        assert False, "expected ProviderError"
    except ProviderError as exc:
        assert exc.code == "invalid_key"
        assert "test-groq-key" not in str(exc)
        assert "API" in exc.user_message or "unavailable" in exc.user_message.lower()
    get_settings.cache_clear()


def test_groq_failure_falls_back_to_deterministic(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    get_settings.cache_clear()

    def boom(*a, **k):
        raise ProviderError("timeout")

    monkeypatch.setattr("app.ai.providers.groq.GroqProvider.generate", boom)
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    res = client.post("/api/ai/chat", headers=headers, json={"message": "How is my portfolio performing?"})
    assert res.status_code == 200
    body = res.json()
    assert body["provider"] == "deterministic"
    assert body["authorized_household"] == "Morgan Family"
    assert "28,10,334" in body["answer"] or "2810334" in body["answer"].replace(",", "")
    assert "$" not in body["answer"] or "₹" in body["answer"]
    blob = json.dumps(body)
    assert "test-groq-key" not in blob
    get_settings.cache_clear()


def test_status_never_returns_groq_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    get_settings.cache_clear()
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    status = client.get("/api/ai/status", headers=headers).json()
    dumped = json.dumps(status)
    assert "test-groq-key" not in dumped
    assert "api_key" not in dumped.lower()
    assert status["provider"] == "groq"
    assert status["configured"] is True
    assert status["fallback_available"] is True
    assert status["model"]
    get_settings.cache_clear()


def test_groq_path_does_not_send_chen_context_for_morgan(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    get_settings.cache_clear()
    captured = {}

    def fake_generate(self, *, system_prompt, user_message, context, documents):
        captured["context"] = context
        captured["documents"] = documents
        captured["message"] = user_message
        return {
            "answer": f"Authorized {context.get('household', {}).get('name')} only.",
            "model": self.model,
            "token_usage": {},
            "sources": ["test"],
            "assumptions": [],
            "limitations": [],
            "disclaimer": "d",
        }

    monkeypatch.setattr("app.ai.providers.groq.GroqProvider.generate", fake_generate)
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    refused = client.post("/api/ai/chat", headers=headers, json={"message": "What is Chen Family's portfolio?"}).json()
    assert refused["refused"] is True
    assert "context" not in captured
    ok = client.post("/api/ai/chat", headers=headers, json={"message": "How is my portfolio performing?"}).json()
    assert ok["authorized_household"] == "Morgan Family"
    assert captured["context"]["household"]["name"] == "Morgan Family"
    blob = json.dumps(captured["context"], default=str)
    assert "Chen Family" not in blob
    get_settings.cache_clear()
