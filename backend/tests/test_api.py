from tests.conftest import auth_header, make_client


def test_duplicate_rebalance_preview_idempotent():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    headers["Idempotency-Key"] = "rebalance-test-1"
    a = client.post("/api/rebalance/preview", headers=headers, json={"portfolio_id": 1})
    b = client.post("/api/rebalance/preview", headers=headers, json={"portfolio_id": 1})
    assert a.status_code == 200
    assert b.status_code == 200
    assert a.json()["book_of_record_modified"] is False
    assert a.json()["rebalance_id"] == b.json()["rebalance_id"]


def test_approval_flow_does_not_mutate_book():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    created = client.post(
        "/api/approvals",
        headers=headers,
        json={"action": "rebalance", "entity_type": "Portfolio", "entity_id": "1", "notes": "preview"},
    )
    assert created.status_code == 200
    decided = client.post(
        f"/api/approvals/{created.json()['id']}/decide",
        headers=headers,
        json={"status": "approved", "notes": "ok"},
    )
    assert decided.status_code == 200
    assert decided.json()["book_of_record_modified"] is False
    again = client.post(
        f"/api/approvals/{created.json()['id']}/decide",
        headers=headers,
        json={"status": "rejected", "notes": "late"},
    )
    assert again.status_code == 409


def test_audit_has_no_delete_route():
    client = make_client()
    headers = auth_header(client, "sarah.wilson@nexgile.demo")
    res = client.delete("/api/audit", headers=headers)
    assert res.status_code in (404, 405)


def test_health_and_ready():
    client = make_client()
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/health/live").status_code == 200
    ready = client.get("/api/health/ready")
    assert ready.status_code == 200


def test_ai_scoped_to_user():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    res = client.post("/api/ai/chat", headers=headers, json={"message": "How is my portfolio performing?"})
    assert res.status_code == 200
    body = res.json()
    assert body["authorized_household"] == "Morgan Family"
    assert body["disclaimer"]
    assert body["advisor_review_required"] is True


def test_stale_lineage_fields_present():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    dash = client.get("/api/dashboard", headers=headers).json()
    assert dash["lineage"]["data_quality_status"] in {"FRESH", "STALE", "DEGRADED", "RECONCILIATION_REQUIRED"}
    assert "realtime" in dash["lineage"]
    assert dash["lineage"]["display"]["as_of"]
