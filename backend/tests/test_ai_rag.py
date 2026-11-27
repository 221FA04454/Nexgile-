from tests.conftest import auth_header, make_client
from app.db.session import SessionLocal
from app.models import entities as m
from app.ai.rag.retrieve import retrieve_relevant_documents
from app.ai.rag.chunk import chunk_text
from app.ai.rag.extract import extract_text
from app.ai.providers import resolve_provider
from app.ai.providers.deterministic import DeterministicProvider
from app.ai.intents import classify_intent
from app.ai.prompts import get_prompt, prompt_name_for_intent
from app.ai.context import build_authorized_context
from app.core.config import get_settings
from app.ai.guardrails import sanitize_answer


def test_sanitize_keeps_not_a_guarantee_tax_language():
    text = "INTC and NKE harvests are identified. This is not a guaranteed tax saving."
    out = sanitize_answer(text)
    assert "INTC" in out
    assert "not a guaranteed" in out.lower()


def test_sanitize_blocks_claimed_execution():
    out = sanitize_answer("I have executed the trade in the brokerage account.")
    assert "cannot execute" in out.lower()
    assert "I have executed" not in out


def test_chunk_creation():
    parts = chunk_text("alpha " * 200, size=80, overlap=10)
    assert len(parts) > 1


def test_extract_plaintext():
    text, extractor = extract_text(b"IPS equity target 62 percent", "text/plain", "note.txt")
    assert "equity target" in text
    assert extractor == "plaintext"


def test_intent_and_prompt_version():
    assert classify_intent("How is my portfolio performing?") == "PORTFOLIO_PERFORMANCE"
    assert classify_intent("What tax opportunities do I have?") == "TAX_OPPORTUNITY"
    assert classify_intent("Am I on track for retirement?") == "RETIREMENT_READINESS"
    assert classify_intent("What documents need my attention?") == "DOCUMENT_QUERY"
    assert prompt_name_for_intent("PORTFOLIO_PERFORMANCE") == "portfolio_explanation_v1"
    client = make_client()
    db = SessionLocal()
    try:
        text, version = get_prompt(db, "wealth_assistant_v1")
        assert "Nexgile WealthAgent" in text
        assert version
        assert db.query(m.PromptTemplate).count() >= 4
        assert db.query(m.DocumentChunk).count() >= 1
    finally:
        db.close()
    assert client.get("/api/health/live").status_code == 200


def test_deterministic_provider_is_default_without_groq_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")
    get_settings.cache_clear()
    provider = resolve_provider()
    assert isinstance(provider, DeterministicProvider)
    get_settings.cache_clear()


def test_ai_response_schema_and_morgan_values():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    port = client.get("/api/portfolios", headers=headers).json()
    mv = int(round(port["summary"]["total_market_value"]))
    res = client.post("/api/ai/chat", headers=headers, json={"message": "How is my portfolio performing?"})
    assert res.status_code == 200
    body = res.json()
    assert body["authorized_household"] == "Morgan Family"
    assert body["advisor_review_required"] is True
    assert body["disclaimer"]
    assert body["as_of"]
    assert body["prompt_version"]
    assert body["prompt_name"] == "portfolio_explanation_v1"
    assert body["limitations"]
    assert body["sources"]
    assert body["assumptions"]
    assert body["provider"] == "deterministic"
    assert f"{mv:,}" in body["answer"] or str(mv) in body["answer"].replace(",", "")
    assert "Chen" not in body["answer"]


def test_ai_uses_tax_from_postgres():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    tax = client.get("/api/tax/opportunities", headers=headers).json()
    res = client.post("/api/ai/chat", headers=headers, json={"message": "What tax opportunities do I have?"}).json()
    symbols = {h["symbol"] for h in tax["harvests"]}
    assert symbols
    assert any(sym in res["answer"] for sym in symbols)
    assert res["authorized_household"] == "Morgan Family"
    assert "not a guaranteed tax saving" in res["answer"].lower() or "not a guaranteed" in res["answer"].lower()


def test_documents_query_uses_authorized_vault():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    docs = client.get("/api/documents", headers=headers).json()
    res = client.post("/api/ai/chat", headers=headers, json={"message": "What documents need my attention?"}).json()
    assert res["authorized_household"] == "Morgan Family"
    names = {d["name"] for d in docs["documents"]}
    assert "Chen Family IPS" not in names
    assert "Chen Family IPS" not in res["answer"]
    assert "Last Will" in res["answer"] or "directive" in res["answer"].lower() or "review" in res["answer"].lower()


def test_chen_gets_chen_not_morgan():
    client = make_client()
    morgan = auth_header(client, "alex.morgan@nexgile.demo")
    chen = auth_header(client, "david.chen@nexgile.demo")
    m_ans = client.post("/api/ai/chat", headers=morgan, json={"message": "Summarize my household finances."}).json()
    c_ans = client.post("/api/ai/chat", headers=chen, json={"message": "Summarize my household finances."}).json()
    assert m_ans["authorized_household"] == "Morgan Family"
    assert c_ans["authorized_household"] == "Chen Family"
    assert "Chen Family" not in m_ans["answer"]
    assert "Morgan Family" not in c_ans["answer"]
    m_port = client.get("/api/portfolios", headers=morgan).json()["summary"]["total_market_value"]
    c_port = client.get("/api/portfolios", headers=chen).json()["summary"]["total_market_value"]
    assert int(round(m_port)) != int(round(c_port))


def test_morgan_cannot_ask_about_chen():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    res = client.post("/api/ai/chat", headers=headers, json={"message": "What is Chen Family's portfolio?"})
    assert res.status_code == 200
    body = res.json()
    assert body["refused"] is True
    assert body["intent"] == "CROSS_HOUSEHOLD_PROBE"
    assert "not authorized" in body["answer"].lower()
    assert "422" not in body["answer"]


def test_morgan_cannot_retrieve_chen_document():
    """Morgan AI request for a Chen document yields zero authorized retrieval results."""
    client = make_client()
    db = SessionLocal()
    try:
        morgan = db.query(m.User).filter(m.User.email == "alex.morgan@nexgile.demo").first()
        chen_hh = db.query(m.Household).filter(m.Household.name == "Chen Family").first()
        chen_doc = db.query(m.Document).filter(m.Document.household_id == chen_hh.id).first()
        assert chen_doc is not None
        hits = retrieve_relevant_documents(db, morgan, chen_doc.name, k=20)
        assert all(h["document_id"] != chen_doc.id for h in hits)
        assert all(h["household_id"] != chen_hh.id for h in hits)
        ctx = build_authorized_context(db, morgan, "DOCUMENT_QUERY")
        assert ctx["household"]["id"] == morgan.household_id
        assert chen_hh.id not in ctx["allowed_household_ids"]
        doc_names = [d["name"] for d in (ctx.get("documents") or {}).get("documents") or []]
        assert chen_doc.name not in doc_names
    finally:
        db.close()

    headers = auth_header(client, "alex.morgan@nexgile.demo")
    search = client.post("/api/ai/search", headers=headers, json={"message": "Chen Family IPS"})
    assert search.status_code == 200
    body = search.json()
    assert body["count"] == 0
    assert body["results"] == []
    assert body.get("authorized") is False


def test_rag_does_not_return_chen_chunks_to_morgan():
    client = make_client()
    db = SessionLocal()
    try:
        morgan = db.query(m.User).filter(m.User.email == "alex.morgan@nexgile.demo").first()
        chen_hh = db.query(m.Household).filter(m.Household.name == "Chen Family").first()
        hits = retrieve_relevant_documents(db, morgan, "Chen Family IPS portfolio statement", k=10)
        assert all(h["household_id"] != chen_hh.id for h in hits)
        assert all(h["household_id"] == morgan.household_id for h in hits)
    finally:
        db.close()
    assert client.get("/api/health/live").status_code == 200


def test_document_ingest_and_ai_audit():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    files = {"file": ("ips-note.txt", b"Morgan Family investment policy equity target 62 percent.", "text/plain")}
    up = client.post("/api/documents/upload", headers=headers, files=files)
    assert up.status_code == 200
    doc_id = up.json()["id"]
    db = SessionLocal()
    try:
        chunks = db.query(m.DocumentChunk).filter(m.DocumentChunk.document_id == doc_id).all()
        assert chunks
        assert chunks[0].household_id is not None
        assert chunks[0].embedding
        versions = db.query(m.DocumentVersion).filter(m.DocumentVersion.document_id == doc_id).all()
        assert versions
        assert "equity target" in (versions[0].extracted_text or "")
    finally:
        db.close()
    client.post("/api/ai/chat", headers=headers, json={"message": "What documents need my attention?"})
    db = SessionLocal()
    try:
        rows = db.query(m.AIInteraction).filter(m.AIInteraction.user_email == "alex.morgan@nexgile.demo").all()
        assert rows
        last = rows[-1]
        assert last.prompt_version
        assert last.intent
        assert last.provider == "deterministic"
        assert last.request_id is not None
        assert db.query(m.AuditEvent).filter(m.AuditEvent.action == "ai_chat").count() >= 1
    finally:
        db.close()


def test_ai_status_and_sources_authorized_only():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    status = client.get("/api/ai/status", headers=headers).json()
    blob = str(status).lower()
    assert "api_key" not in blob
    assert "gsk_" not in blob
    assert status["fallback_available"] is True
    if not get_settings().groq_api_key:
        assert status["provider"] == "deterministic"
        assert status["configured"] is False or status["requested_provider"] != "groq"
    sources = client.get("/api/ai/sources", headers=headers, params={"q": "trust will directive"}).json()
    db = SessionLocal()
    try:
        morgan = db.query(m.User).filter(m.User.email == "alex.morgan@nexgile.demo").first()
        chen_hh = db.query(m.Household).filter(m.Household.name == "Chen Family").first()
        morgan_id = morgan.household_id
        chen_id = chen_hh.id
    finally:
        db.close()
    assert all(r["household_id"] == morgan_id for r in sources["results"])
    assert all(r["household_id"] != chen_id for r in sources["results"])
