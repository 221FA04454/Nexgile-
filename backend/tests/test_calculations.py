from app.calculations import engine as calc


class H:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", 1)
        self.account_id = 1
        self.symbol = kwargs.get("symbol", "VTI")
        self.name = kwargs.get("name", "Vanguard")
        self.asset_class = kwargs.get("asset_class", "Equities")
        self.sector = "Blend"
        self.region = "US"
        self.quantity = kwargs.get("quantity", 10)
        self.price = kwargs.get("price", 100)
        self.cost_basis = kwargs.get("cost_basis", 800)
        self.day_change_pct = 0.1
        self.ytd_return_pct = 10
        self.as_of = "2026-09-07"


def test_holdings_summary_math():
    rows = [
        H(id=1, quantity=2, price=50, cost_basis=80, symbol="A"),
        H(id=2, quantity=1, price=100, cost_basis=90, symbol="B", asset_class="Cash"),
    ]
    s = calc.holdings_summary(rows)
    assert s["total_market_value"] == 200
    assert s["total_cost_basis"] == 170
    assert s["unrealized_gain_loss"] == 30
    assert s["book_of_record_mutated"] is False
    assert s["as_of"]
    assert "fees" in s


def test_funding_and_projection():
    assert calc.funding_pct(50, 100) == 50
    assert calc.goal_projection(100, 0, 1, 0.1) == 110


def test_tax_impact_loss_is_benefit():
    r = calc.estimated_tax_impact(-1000, True)
    assert r["estimated_benefit"] > 0
    assert r["estimated_tax"] == 0
    assert r["limitations"]


def test_rebalance_is_preview_only():
    summary = calc.holdings_summary([H(quantity=10, price=100, cost_basis=900, asset_class="Equities")])
    preview = calc.rebalance_preview(summary, {"equity": 0.62, "fixed_income": 0.22, "alternatives": 0.08, "cash": 0.06, "other": 0.02})
    assert preview["book_of_record_modified"] is False
    assert preview["approval_required"] is True


def test_monte_carlo_deterministic_seed():
    a = calc.monte_carlo(100000, 1000, years=3, n=50)
    b = calc.monte_carlo(100000, 1000, years=3, n=50)
    assert a["p50"] == b["p50"]
    assert a["book_of_record_mutated"] is False
