from app.core.currency import DEFAULT_CURRENCY, DEFAULT_LOCALE, format_inr, indian_grouped_int, with_currency
from tests.conftest import auth_header, make_client


def test_indian_grouping_examples():
    assert format_inr(1000) == "₹1,000"
    assert format_inr(10000) == "₹10,000"
    assert format_inr(100000) == "₹1,00,000"
    assert format_inr(1000000) == "₹10,00,000"
    assert format_inr(10000000) == "₹1,00,00,000"


def test_zero_negative_decimal_large():
    assert format_inr(0) == "₹0"
    assert format_inr(-1000) == "₹-1,000" or format_inr(-1000) == "-₹1,000"
    assert format_inr(1234.56, 2) == "₹1,234.56"
    assert format_inr(2810334.3) == "₹28,10,334"
    assert indian_grouped_int(2140000) == "21,40,000"


def test_portfolio_tax_retirement_goal_values():
    assert format_inr(2810334.3) == "₹28,10,334"
    assert format_inr(42600) == "₹42,600"
    assert format_inr(210000) == "₹2,10,000"
    assert format_inr(3000000) == "₹30,00,000"
    assert format_inr(2140000) == "₹21,40,000"
    assert format_inr(2500000) == "₹25,00,000"
    assert format_inr(1850000) == "₹18,50,000"
    assert format_inr(650000) == "₹6,50,000"


def test_currency_metadata_and_numeric_payload():
    payload = with_currency({"value": 1000000})
    assert payload["value"] == 1000000
    assert payload["currency"] == DEFAULT_CURRENCY == "INR"
    assert payload["locale"] == DEFAULT_LOCALE == "en-IN"
    assert payload["currency_symbol"] == "₹"
    assert "₹10,00,000" not in str(payload["value"])


def test_dashboard_and_reports_expose_inr_not_usd():
    client = make_client()
    headers = auth_header(client, "alex.morgan@nexgile.demo")
    dash = client.get("/api/dashboard", headers=headers).json()
    assert dash["currency"] == "INR"
    assert dash["locale"] == "en-IN"
    assert isinstance(dash["net_worth"]["total"], (int, float))
    assert dash["net_worth"]["total"] > 1_000_000
    port = client.get("/api/portfolios", headers=headers).json()
    assert port["currency"] == "INR"
    tax = client.get("/api/tax/opportunities", headers=headers).json()
    assert tax["currency"] == "INR"
    goals = client.get("/api/goals", headers=headers).json()
    assert goals["currency"] == "INR"
    reports = client.get("/api/reports", headers=headers).json()
    rid = reports["reports"][0]["id"]
    preview = client.get(f"/api/reports/{rid}", headers=headers).json()
    body = " ".join(s["body"] for s in preview["sections"])
    assert "₹" in body
    assert "$" not in body
    assert "USD" not in body
    chat = client.post("/api/ai/chat", headers=headers, json={"message": "How is my portfolio performing?"}).json()
    assert "₹" in chat["answer"]
    assert "USD" not in chat["answer"]
