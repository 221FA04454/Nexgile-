from tests.conftest import auth_header, make_client
from app.db.session import SessionLocal
from app.db.validate_demo import validate
from app.models import entities as m


def test_seed_passes_relational_validation():
    client = make_client()
    db = SessionLocal()
    try:
        failures = validate(db)
    finally:
        db.close()
    assert failures == [], failures
    _ = client


def test_dashboard_numbers_come_from_holdings():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    dash = client.get("/api/dashboard", headers=headers).json()
    port = client.get("/api/portfolios", headers=headers).json()
    assert dash["household"]["name"] == "Morgan Family"
    assert dash["portfolio"]["invested_assets"] == port["summary"]["total_market_value"]
    assert dash["portfolio"]["invested_assets"] > 1_000_000
    assert dash["balance_sheet"]["other_assets"] == 1_250_000
    assert dash["net_worth"]["liabilities"] == 780_000
    assert "traditional_ira" not in str(dash["household"])
    accounts = client.get("/api/accounts", headers=headers).json()["accounts"]
    types = {a["type"] for a in accounts}
    assert {"brokerage", "401k", "roth_ira", "traditional_ira", "trust", "cash"} <= types


def test_morgan_cannot_read_chen_or_shah_books():
    client = make_client()
    morgan = auth_header(client, "alex.morgan@nexgile.demo")
    chen = auth_header(client, "david.chen@nexgile.demo")
    shah = auth_header(client, "anika.shah@nexgile.demo")

    chen_dash = client.get("/api/dashboard", headers=chen).json()
    shah_dash = client.get("/api/dashboard", headers=shah).json()
    morgan_dash = client.get("/api/dashboard", headers=morgan).json()
    assert chen_dash["household"]["name"] == "Chen Family"
    assert shah_dash["household"]["name"] == "Shah Family"
    assert morgan_dash["household"]["name"] == "Morgan Family"
    assert chen_dash["portfolio"]["invested_assets"] != morgan_dash["portfolio"]["invested_assets"]

    chen_docs = client.get("/api/documents", headers=chen).json()["documents"]
    shah_docs = client.get("/api/documents", headers=shah).json()["documents"]
    morgan_docs = client.get("/api/documents", headers=morgan).json()["documents"]
    chen_ids = {d["id"] for d in chen_docs}
    shah_ids = {d["id"] for d in shah_docs}
    morgan_ids = {d["id"] for d in morgan_docs}
    assert chen_ids.isdisjoint(morgan_ids)
    assert shah_ids.isdisjoint(morgan_ids)

    search = client.get("/api/search", params={"q": "Chen"}, headers=morgan).json()
    clients = search["results"]["clients"]
    assert all("Chen" not in (c.get("label") or "") and "Chen" not in (c.get("sub") or "") for c in clients)


def test_goals_and_tax_are_household_scoped():
    client = make_client()
    morgan = auth_header(client, "alex.morgan@nexgile.demo")
    chen = auth_header(client, "david.chen@nexgile.demo")
    mg = client.get("/api/goals", headers=morgan).json()["goals"]
    cg = client.get("/api/goals", headers=chen).json()["goals"]
    assert {g["name"] for g in mg}.isdisjoint({g["name"] for g in cg})
    mt = client.get("/api/tax/opportunities", headers=morgan).json()
    ct = client.get("/api/tax/opportunities", headers=chen).json()
    assert mt["estimated_liability"] != ct["estimated_liability"] or mt["harvests"][0]["symbol"] != ct["harvests"][0]["symbol"]
