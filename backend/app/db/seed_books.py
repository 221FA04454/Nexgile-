"""Secondary household books so authorization can be demonstrated with real rows."""
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import entities as m

AS_OF = date(2026, 9, 7)


def _add_lots(db: Session, holding: m.Holding) -> None:
    if holding.quantity <= 1:
        return
    db.add(
        m.TaxLot(
            holding_id=holding.id,
            acquired_on=date(2022, 6, 14),
            quantity=round(holding.quantity * 0.6, 4),
            cost_per_share=round((holding.cost_basis / holding.quantity) * 0.9, 4),
            term="long",
        )
    )
    db.add(
        m.TaxLot(
            holding_id=holding.id,
            acquired_on=date(2025, 2, 3),
            quantity=round(holding.quantity * 0.4, 4),
            cost_per_share=round((holding.cost_basis / holding.quantity) * 1.05, 4),
            term="long",
        )
    )


def seed_compact_household(
    db: Session,
    *,
    household: m.Household,
    advisor: m.Advisor,
    owner_name: str,
    custodian_id: int,
    provider: str,
    accounts_spec: list[dict],
    holdings_rows: list[tuple],
    goal_spec: list[dict],
    harvest_symbol: str,
) -> None:
    household.other_assets = household.other_assets or 0
    household.liabilities = household.liabilities or 0
    db.flush()

    accounts = []
    for spec in accounts_spec:
        acct = m.Account(
            household_id=household.id,
            as_of=AS_OF,
            source="custodian",
            provider=provider,
            source_record_id=f"{provider.upper()}-{household.id}-{spec['account_type']}",
            version=1,
            data_quality_status="FRESH",
            updated_at=datetime.utcnow() - timedelta(minutes=8),
            **spec,
        )
        db.add(acct)
        accounts.append(acct)
    db.flush()
    by_name = {a.name: a for a in accounts}

    holdings = []
    for row in holdings_rows:
        acct_name, symbol, name, asset, sector, region, qty, price, cost, day, ytd = row
        acct = by_name[acct_name]
        h = m.Holding(
            account_id=acct.id,
            symbol=symbol,
            name=name,
            asset_class=asset,
            sector=sector,
            region=region,
            quantity=qty,
            price=price,
            cost_basis=cost,
            day_change_pct=day,
            ytd_return_pct=ytd,
            as_of=AS_OF,
            source="market_data",
            provider="internal_pricing",
            source_record_id=f"{provider.upper()}-POS-{symbol}-{acct.id}",
            data_quality_status="FRESH",
            version=4,
            updated_at=datetime.utcnow() - timedelta(minutes=8),
        )
        db.add(h)
        holdings.append(h)
    db.flush()
    for h in holdings:
        _add_lots(db, h)

    totals = {}
    for h in holdings:
        totals.setdefault(h.account_id, {"mv": 0, "cb": 0})
        totals[h.account_id]["mv"] += h.quantity * h.price
        totals[h.account_id]["cb"] += h.cost_basis
    for acct in accounts:
        t = totals.get(acct.id, {"mv": 0, "cb": 0})
        if acct.account_type not in {"real_estate", "liability"}:
            acct.market_value = round(t["mv"], 2)
            acct.cost_basis = round(t["cb"], 2)

    invested = sum(a.market_value or 0 for a in accounts if a.account_type not in {"real_estate", "liability"})
    bench = db.query(m.Benchmark).first()
    portfolio = m.Portfolio(
        household_id=household.id,
        name=f"{household.name} Portfolio",
        strategy=household.risk_profile,
        risk_score=58,
        benchmark_id=bench.id if bench else None,
        as_of=AS_OF,
        source="book_of_record",
        provider="internal",
        source_record_id=f"PORT-{household.id}",
        data_quality_status="FRESH",
        version=1,
    )
    db.add(portfolio)
    db.flush()
    start = invested / 1.09 if invested else 100000
    for i in range(6):
        d = date(2026, 4, 1) + timedelta(days=30 * i)
        if d > AS_OF:
            d = AS_OF
        db.add(
            m.PerformancePoint(
                portfolio_id=portfolio.id,
                as_of=d,
                market_value=round(start * (1 + 0.09 * i / 5), 2),
                benchmark_value=round(start * (1 + 0.07 * i / 5), 2),
            )
        )
    db.add(
        m.Allocation(
            portfolio_id=portfolio.id,
            asset_class="Equities",
            current_pct=0.7,
            target_pct=portfolio.target_equity,
        )
    )
    db.add(
        m.Transaction(
            account_id=accounts[0].id,
            txn_type="contribution",
            description=f"{owner_name} contribution",
            amount=5000,
            occurred_on=date(2026, 8, 15),
            actor=owner_name,
        )
    )

    for spec in goal_spec:
        g = m.Goal(household_id=household.id, **spec)
        db.add(g)
        db.flush()
        db.add_all(
            [
                m.Scenario(goal_id=g.id, name="Base Case", growth_rate=0.065, projected_value=round(g.current_amount * 1.4, 0), probability=g.probability, isolated=True),
                m.Scenario(goal_id=g.id, name="Optimistic", growth_rate=0.09, projected_value=round(g.current_amount * 1.7, 0), probability=min(0.95, g.probability + 0.08), isolated=True),
                m.Scenario(goal_id=g.id, name="Conservative", growth_rate=0.035, projected_value=round(g.current_amount * 1.15, 0), probability=max(0.4, g.probability - 0.12), isolated=True),
            ]
        )

    loss_h = next((h for h in holdings if h.symbol == harvest_symbol), holdings[-1])
    db.add(
        m.Harvest(
            household_id=household.id,
            holding_id=loss_h.id,
            symbol=loss_h.symbol,
            security_name=loss_h.name,
            unrealized_loss=round(loss_h.quantity * loss_h.price - loss_h.cost_basis, 2),
            potential_tax_benefit=1200,
            wash_sale_status="Clear",
            replacement_security="VTI",
            status="proposed",
        )
    )
    db.add(
        m.TaxOpportunity(
            household_id=household.id,
            opportunity_type="tlh",
            title="Tax-loss harvesting",
            detail=f"Harvest {loss_h.symbol} in the {household.name} book.",
            estimated_benefit=1200,
            status="identified",
        )
    )
    db.add(
        m.RMD(
            household_id=household.id,
            account_name=accounts[0].name,
            required_amount=0,
            taken_ytd=0,
            remaining=0,
            deadline=date(2055, 12, 31),
            status="not_required",
        )
    )
    db.add(
        m.Document(
            household_id=household.id,
            name=f"{household.name} IPS",
            category="Investment",
            doc_type="PDF",
            uploaded_on=date(2026, 5, 1),
            version="1.0",
            owner=advisor.name,
            status="current",
            ai_classification="ips",
        )
    )
    db.add(
        m.Report(
            household_id=household.id,
            name=f"{household.name} Snapshot",
            report_type="household_wealth",
            period="September 2026",
            generated_on=AS_OF,
            summary=f"Authorized snapshot for {household.name}.",
        )
    )
    db.add(
        m.Alert(
            household_id=household.id,
            title="Quarterly review",
            body=f"{household.name} quarterly packet is ready.",
            severity="info",
            category="meeting",
        )
    )
    db.add(
        m.EstatePlan(
            household_id=household.id,
            will_status="current",
            trust_status="review_due",
            poa_status="current",
            healthcare_directive_status="current",
            last_review=date(2025, 11, 1),
            next_review=date(2026, 11, 1),
            estate_tax_exposure=0,
            attorney_name="Regional counsel",
            readiness_score=70,
        )
    )
    db.add(
        m.Beneficiary(
            household_id=household.id,
            name=owner_name,
            relationship="Self / spouse plan",
            account_or_trust=accounts[0].name,
            share_pct=100,
            contingent=False,
            last_reviewed=date(2026, 1, 15),
        )
    )
    db.add(
        m.LineageRecord(
            entity_type="Portfolio",
            entity_id=str(portfolio.id),
            source="book_of_record",
            provider="internal",
            source_record_id=f"PORT-{household.id}",
            as_of=AS_OF,
            version=1,
            data_quality_status="FRESH",
        )
    )
    db.add(
        m.AuditEvent(
            user="system",
            actor_role="ADMIN",
            action="seed",
            entity_type="Household",
            entity_id=str(household.id),
            new_value={"name": household.name},
            status="recorded",
            result="success",
            reason="demo_seed",
        )
    )


def seed_other_households(db: Session, advisor: m.Advisor, chen_hh: m.Household, shah_hh: m.Household, patel_hh: m.Household, schwab_id: int, fidelity_id: int) -> None:
    chen_hh.other_assets = 920000
    chen_hh.liabilities = 410000
    chen_hh.emergency_reserve = 45000
    chen_hh.upcoming_needs = 12000
    chen_hh.liquidity_label = "4.1 months of spending"
    chen_hh.estimated_tax_liability = 21400
    chen_hh.capital_gains_budget_used = 8000
    chen_hh.capital_gains_budget_limit = 40000
    chen_hh.carryforward_losses = 0

    shah_hh.other_assets = 640000
    shah_hh.liabilities = 280000
    shah_hh.emergency_reserve = 38000
    shah_hh.upcoming_needs = 9000
    shah_hh.liquidity_label = "5.0 months of spending"
    shah_hh.estimated_tax_liability = 9800
    shah_hh.capital_gains_budget_used = 2200
    shah_hh.capital_gains_budget_limit = 25000
    shah_hh.carryforward_losses = 1500

    patel_hh.other_assets = 510000
    patel_hh.liabilities = 190000
    patel_hh.emergency_reserve = 24000
    patel_hh.upcoming_needs = 6000
    patel_hh.liquidity_label = "3.8 months of spending"
    patel_hh.estimated_tax_liability = 7200
    patel_hh.capital_gains_budget_used = 1000
    patel_hh.capital_gains_budget_limit = 20000
    patel_hh.carryforward_losses = 0

    seed_compact_household(
        db,
        household=chen_hh,
        advisor=advisor,
        owner_name="David Chen",
        custodian_id=schwab_id,
        provider="schwab",
        accounts_spec=[
            dict(name="Chen Brokerage", account_type="brokerage", account_number_masked="•••• 6112", tax_status="taxable", cash_balance=18400, owner_name="David Chen", custodian_id=schwab_id),
            dict(name="Chen 401(k)", account_type="401k", account_number_masked="•••• 4481", tax_status="tax-deferred", cash_balance=3200, owner_name="David Chen", custodian_id=fidelity_id),
            dict(name="Chen Cash", account_type="cash", account_number_masked="•••• 2201", tax_status="taxable", cash_balance=62000, owner_name="David Chen", custodian_id=schwab_id),
        ],
        holdings_rows=[
            ("Chen Brokerage", "AAPL", "Apple Inc.", "Equities", "Technology", "US", 180, 228.40, 28000, 0.42, 18.4),
            ("Chen Brokerage", "VTI", "Vanguard Total Stock Market ETF", "Equities", "Blend", "US", 420, 286.15, 98000, 0.31, 16.4),
            ("Chen Brokerage", "BND", "Vanguard Total Bond Market ETF", "Fixed Income", "Bonds", "US", 900, 73.85, 72000, -0.12, 1.4),
            ("Chen 401(k)", "FXAIX", "Fidelity 500 Index Fund", "Equities", "Blend", "US", 610, 218.40, 118000, 0.26, 15.2),
            ("Chen Cash", "SGOV", "iShares 0-3 Month Treasury", "Cash", "Cash", "US", 610, 100.42, 61000, 0.01, 3.9),
        ],
        goal_spec=[
            dict(name="Retirement — Chen", category="Retirement", target_amount=2200000, current_amount=890000, target_date=date(2044, 1, 1), probability=0.71, projected_status="Watch", linked_accounts=["Chen 401(k)", "Chen Brokerage"], annual_contribution=48000, notes="Growth-oriented plan."),
        ],
        harvest_symbol="BND",
    )
    seed_compact_household(
        db,
        household=shah_hh,
        advisor=advisor,
        owner_name="Anika Shah",
        custodian_id=schwab_id,
        provider="schwab",
        accounts_spec=[
            dict(name="Shah Brokerage", account_type="brokerage", account_number_masked="•••• 7744", tax_status="taxable", cash_balance=9600, owner_name="Anika Shah", custodian_id=schwab_id),
            dict(name="Shah Roth IRA", account_type="roth_ira", account_number_masked="•••• 3310", tax_status="tax-free", cash_balance=2100, owner_name="Anika Shah", custodian_id=schwab_id),
        ],
        holdings_rows=[
            ("Shah Brokerage", "MSFT", "Microsoft Corp.", "Equities", "Technology", "US", 90, 431.20, 31000, 0.18, 14.2),
            ("Shah Brokerage", "VOO", "Vanguard S&P 500 ETF", "Equities", "Blend", "US", 120, 548.30, 52000, 0.28, 15.9),
            ("Shah Roth IRA", "VXUS", "Vanguard Total International Stock", "Equities", "International", "Intl", 800, 64.20, 48000, 0.17, 8.1),
        ],
        goal_spec=[
            dict(name="Home purchase", category="Major Purchase", target_amount=180000, current_amount=72000, target_date=date(2029, 6, 1), probability=0.66, projected_status="Watch", linked_accounts=["Shah Brokerage"], annual_contribution=18000, notes="Down payment sleeve."),
        ],
        harvest_symbol="VXUS",
    )
    seed_compact_household(
        db,
        household=patel_hh,
        advisor=advisor,
        owner_name="Priya Patel",
        custodian_id=fidelity_id,
        provider="fidelity",
        accounts_spec=[
            dict(name="Patel Brokerage", account_type="brokerage", account_number_masked="•••• 9091", tax_status="taxable", cash_balance=5400, owner_name="Priya Patel", custodian_id=fidelity_id),
            dict(name="Patel IRA", account_type="traditional_ira", account_number_masked="•••• 1188", tax_status="tax-deferred", cash_balance=1800, owner_name="Priya Patel", custodian_id=fidelity_id),
        ],
        holdings_rows=[
            ("Patel Brokerage", "VTI", "Vanguard Total Stock Market ETF", "Equities", "Blend", "US", 210, 286.15, 52000, 0.31, 16.4),
            ("Patel IRA", "BND", "Vanguard Total Bond Market ETF", "Fixed Income", "Bonds", "US", 700, 73.85, 56000, -0.12, 1.4),
        ],
        goal_spec=[
            dict(name="Practice buy-in", category="Career", target_amount=350000, current_amount=118000, target_date=date(2030, 1, 1), probability=0.58, projected_status="Needs Attention", linked_accounts=["Patel Brokerage"], annual_contribution=22000, notes="Medical practice capital."),
        ],
        harvest_symbol="BND",
    )
    db.add(
        m.Gift(
            household_id=chen_hh.id,
            charity_name="Stanford Education Fund",
            gift_type="cash",
            amount=5000,
            gifted_on=date(2026, 4, 20),
            tax_deduction_estimate=5000,
        )
    )
    db.add(
        m.DAF(
            household_id=shah_hh.id,
            name="Shah Family DAF",
            balance=12400,
            ytd_grants=2000,
            sponsor="Schwab Charitable",
        )
    )
