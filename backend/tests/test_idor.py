from tests.conftest import auth_header, make_client


def test_client_cannot_list_advisor_workstation():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    res = client.get("/api/advisors/clients", headers=headers)
    assert res.status_code == 403


def test_client_cannot_read_another_household_report():
    client = make_client()
    alex = auth_header(client, "alex.morgan@nexgile.demo")
    reports = client.get("/api/reports", headers=alex).json()["reports"]
    assert reports
    morgan_report_id = reports[0]["id"]
    patel = auth_header(client, "priya.patel@nexgile.demo")
    res = client.get(f"/api/reports/{morgan_report_id}", headers=patel)
    assert res.status_code in (403, 404)


def test_client_search_does_not_leak_other_households():
    client = make_client()
    headers = auth_header(client, "priya.patel@nexgile.demo")
    res = client.get("/api/search", params={"q": "Morgan"}, headers=headers)
    assert res.status_code == 200
    clients = res.json()["results"]["clients"]
    assert all("Morgan" not in (c.get("label") or "") and "Morgan" not in (c.get("sub") or "") for c in clients)


def test_advisor_cannot_open_unassigned_if_none():
    client = make_client()
    headers = auth_header(client, "sarah.wilson@nexgile.demo")
    res = client.get("/api/advisors/clients/99999", headers=headers)
    assert res.status_code in (403, 404)


def test_participant_dashboard_is_not_morgan_book():
    client = make_client()
    headers = auth_header(client, "priya.shah@nexgile.demo")
    dash = client.get("/api/dashboard", headers=headers).json()
    assert dash["household"]["name"] != "Morgan Family"


def test_unauthorized_approval_decision():
    client = make_client()
    alex = auth_header(client, "alex.morgan@nexgile.demo")
    created = client.post(
        "/api/approvals",
        headers=alex,
        json={"action": "tax_harvest", "entity_type": "Harvest", "entity_id": "x", "notes": "n"},
    )
    approval_id = created.json()["id"]
    patel = auth_header(client, "priya.patel@nexgile.demo")
    res = client.post(
        f"/api/approvals/{approval_id}/decide",
        headers=patel,
        json={"status": "approved", "notes": "nope"},
    )
    assert res.status_code in (403, 409, 404)
