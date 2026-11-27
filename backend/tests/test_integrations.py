import json

from tests.conftest import auth_header, make_client
from app.db.session import SessionLocal
from app.models import entities as m
from app.integrations.providers import FlakyProvider, PermanentFailProvider
from app.integrations.registry import ADAPTERS, catalog
from app.integrations.sync import run_sync


def test_catalog_covers_required_categories():
    cats = {p.category for p in ADAPTERS.values()}
    assert {"financial", "business", "retirement", "communication", "identity", "documents"} <= cats
    health = catalog()
    assert all(item["live"] is False for item in health)
    assert any(p.key == "custodian" for p in ADAPTERS.values())
    assert any(p.key == "broker_dealer" for p in ADAPTERS.values())
    assert any(p.key == "identity_sso" for p in ADAPTERS.values())


def test_retry_then_success():
    out = FlakyProvider().execute("sync", {})
    assert out["ok"] is True
    assert out["attempt"] == 2


def test_permanent_failure_is_not_retried_endlessly():
    out = PermanentFailProvider().execute("sync", {})
    assert out["ok"] is False
    assert out["error"] == "invalid_credentials"
    assert "credential" not in (out.get("message") or "").lower() or "unavailable" in out["message"].lower() or "could not" in out["message"].lower()


def test_broker_never_executes_live_trade():
    data = ADAPTERS["broker_dealer"].fetch(operation="execute", payload={}, request_id="r", correlation_id="c")
    assert data["orders"][0]["executed"] is False
    assert data["orders"][0]["book_of_record_modified"] is False


def test_communication_does_not_send():
    data = ADAPTERS["email"].fetch(operation="send", payload={"to": "a@b.c"}, request_id="r", correlation_id="c")
    assert data["delivered"] is False
    assert data["sandbox"] is True


def test_client_cannot_access_integration_admin():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    assert client.get("/api/integrations", headers=headers).status_code == 403
    assert client.get("/api/integrations/status", headers=headers).status_code == 403
    assert client.post("/api/integrations/custodian/sync", headers=headers).status_code == 403
    assert client.get("/api/integrations/reconciliation", headers=headers).status_code == 403


def test_advisor_integrations_hide_secrets():
    client = make_client()
    headers = auth_header(client, "sarah.wilson@nexgile.demo")
    res = client.get("/api/integrations", headers=headers)
    assert res.status_code == 200
    body = res.json()
    blob = json.dumps(body).lower()
    assert "api_key" not in blob
    assert "gsk_" not in blob
    assert "password" not in blob
    assert body["integrations"]
    health = client.get("/api/integrations/custodian/health", headers=headers).json()
    assert health["credentials_configured"] is False
    assert health["live"] is False


def test_sync_is_idempotent_and_does_not_duplicate_accounts():
    client = make_client()
    headers = auth_header(client, "sarah.wilson@nexgile.demo")
    db = SessionLocal()
    try:
        before = db.query(m.Account).count()
        holdings_before = db.query(m.Holding).count()
        lots_before = db.query(m.TaxLot).count()
        participants_before = db.query(m.Participant).count()
    finally:
        db.close()
    first = client.post("/api/integrations/custodian/sync", headers=headers)
    assert first.status_code == 200
    second = client.post("/api/integrations/custodian/sync", headers=headers)
    assert second.status_code == 200
    assert second.json()["created"] == 0
    db = SessionLocal()
    try:
        assert db.query(m.Account).count() == before
        assert db.query(m.Holding).count() == holdings_before
        assert db.query(m.TaxLot).count() == lots_before
        assert db.query(m.Participant).count() == participants_before
        assert db.query(m.Account).filter(m.Account.name == "Unmatched custodian shadow account").count() == 0
        links = db.query(m.IntegrationRecordLink).filter(m.IntegrationRecordLink.provider_key == "custodian").count()
        assert links >= 1
        recon = db.query(m.ReconciliationException).filter(m.ReconciliationException.external_id == "SCHWAB-ORPHAN-UNMATCHED").count()
        assert recon >= 1
    finally:
        db.close()


def test_failed_sync_does_not_corrupt_books():
    client = make_client()
    db = SessionLocal()
    try:
        before_ids = {a.id for a in db.query(m.Account).all()}
        before_values = {a.id: a.market_value for a in db.query(m.Account).all()}
        run = run_sync(db, "custodian", actor="test", actor_role="ADMIN", request_id="ok-1")
        assert run.status == "success"
        perm = PermanentFailProvider()
        out = perm.execute("sync", {}, db=db)
        assert out["ok"] is False
        after_ids = {a.id for a in db.query(m.Account).all()}
        after_values = {a.id: a.market_value for a in db.query(m.Account).all()}
        assert after_ids == before_ids
        assert after_values == before_values
    finally:
        db.close()


def test_lineage_and_freshness_recorded():
    client = make_client()
    headers = auth_header(client, "sarah.wilson@nexgile.demo")
    client.post("/api/integrations/crm/sync", headers=headers)
    db = SessionLocal()
    try:
        conn = db.query(m.IntegrationConnection).filter(m.IntegrationConnection.provider_key == "crm").first()
        assert conn.last_success_at is not None
        assert conn.freshness == "FRESH"
        lineage = db.query(m.LineageRecord).filter(m.LineageRecord.provider == "crm").count()
        assert lineage >= 1
        audit = db.query(m.AuditEvent).filter(m.AuditEvent.action == "integration_sync").count()
        assert audit >= 1
        for ev in db.query(m.AuditEvent).filter(m.AuditEvent.action == "integration_sync").all():
            blob = json.dumps(ev.new_value or {})
            assert "gsk_" not in blob
            assert "api_key" not in blob.lower()
    finally:
        db.close()


def test_retirement_sync_links_participants():
    client = make_client()
    headers = auth_header(client, "sarah.wilson@nexgile.demo")
    res = client.post("/api/integrations/recordkeeper/sync", headers=headers)
    assert res.status_code == 200
    db = SessionLocal()
    try:
        n = db.query(m.IntegrationRecordLink).filter(m.IntegrationRecordLink.entity_type == "participant").count()
        assert n >= 1
    finally:
        db.close()


def test_groq_ai_regression_still_scoped():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    res = client.post("/api/ai/chat", headers=headers, json={"message": "How is my portfolio performing?"})
    assert res.status_code == 200
    body = res.json()
    assert body["authorized_household"] == "Morgan Family"
    assert "Chen" not in body["answer"]
    refused = client.post("/api/ai/chat", headers=headers, json={"message": "What is Chen Family's portfolio?"}).json()
    assert refused["refused"] is True
