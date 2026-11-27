from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.seed_books import seed_other_households
from app.models import entities as m

AS_OF = date(2026, 9, 7)


def seed_if_empty(db: Session) -> None:
    from app.core.config import get_settings
    from app.db.seed_ai import seed_ai_layer
    from app.db.convert_inr import apply_inr_book

    if not get_settings().allow_demo_seed:
        return
    if not db.query(m.User).first():
        seed(db)
    seed_ai_layer(db)
    from app.db.seed_integrations import seed_integrations

    seed_integrations(db)
    apply_inr_book(db)


def seed(db: Session) -> None:
    advisor = m.Advisor(
        name="Sarah Wilson",
        email="sarah.wilson@nexgile.demo",
        title="Managing Director, Private Client Group",
        team="Nexgile Wealth",
        phone="(415) 555-0148",
        credentials="CFP®, CFA, CPWA®",
    )
    db.add(advisor)
    db.flush()

    household = m.Household(
        name="Morgan Family",
        primary_client_name="Alex Morgan",
        risk_profile="Moderate Growth",
        domicile="San Francisco, California",
        tax_filing_status="Married Filing Jointly",
        advisor_id=advisor.id,
        other_assets=1250000,
        liabilities=780000,
        emergency_reserve=120000,
        upcoming_needs=28000,
        liquidity_label="6.4 months of spending",
        estimated_tax_liability=86400,
        capital_gains_budget_used=38400,
        capital_gains_budget_limit=81000,
        carryforward_losses=12400,
    )
    db.add(household)
    db.flush()

    chen_hh = m.Household(
        name="Chen Family",
        primary_client_name="David Chen",
        risk_profile="Growth",
        domicile="Palo Alto, California",
        tax_filing_status="Married Filing Jointly",
        advisor_id=advisor.id,
    )
    patel_hh = m.Household(
        name="Patel Household",
        primary_client_name="Priya Patel",
        risk_profile="Balanced",
        domicile="Austin, Texas",
        tax_filing_status="Single",
        advisor_id=advisor.id,
    )
    shah_hh = m.Household(
        name="Shah Family",
        primary_client_name="Anika Shah",
        risk_profile="Moderate",
        domicile="Seattle, Washington",
        tax_filing_status="Married Filing Jointly",
        advisor_id=advisor.id,
    )
    db.add_all([chen_hh, patel_hh, shah_hh])
    db.flush()

    users = [
        m.User(
            email="alex.morgan@nexgile.demo",
            full_name="Alex Morgan",
            hashed_password=hash_password("demo123"),
            role="CLIENT",
            title="Chief Product Officer",
            phone="(415) 555-0192",
            avatar_initials="AM",
            household_id=household.id,
            advisor_id=advisor.id,
            email_verified=True,
        ),
        m.User(
            email="jordan.morgan@nexgile.demo",
            full_name="Jordan Morgan",
            hashed_password=hash_password("demo123"),
            role="CLIENT",
            title="Partner, Architecture",
            phone="(415) 555-0193",
            avatar_initials="JM",
            household_id=household.id,
            advisor_id=advisor.id,
        ),
        m.User(
            email="sarah.wilson@nexgile.demo",
            full_name="Sarah Wilson",
            hashed_password=hash_password("demo123"),
            role="ADVISOR",
            title="Managing Director",
            phone="(415) 555-0148",
            avatar_initials="SW",
            advisor_id=advisor.id,
        ),
        m.User(
            email="maria.chen@nexgile.demo",
            full_name="Maria Chen",
            hashed_password=hash_password("demo123"),
            role="SPONSOR",
            title="VP, Total Rewards — Helios Dynamics",
            phone="(650) 555-0110",
            avatar_initials="MC",
        ),
        m.User(
            email="priya.shah@nexgile.demo",
            full_name="Priya Shah",
            hashed_password=hash_password("demo123"),
            role="PARTICIPANT",
            title="Staff Engineer",
            phone="(650) 555-0177",
            avatar_initials="PS",
        ),
        m.User(
            email="admin@nexgile.demo",
            full_name="Nexgile Admin",
            hashed_password=hash_password("demo123"),
            role="ADMIN",
            title="Platform Administrator",
            avatar_initials="NA",
        ),
        m.User(
            email="david.chen@nexgile.demo",
            full_name="David Chen",
            hashed_password=hash_password("demo123"),
            role="CLIENT",
            title="Founder",
            avatar_initials="DC",
            household_id=chen_hh.id,
            advisor_id=advisor.id,
        ),
        m.User(
            email="anika.shah@nexgile.demo",
            full_name="Anika Shah",
            hashed_password=hash_password("demo123"),
            role="CLIENT",
            title="Product Manager",
            avatar_initials="AS",
            household_id=shah_hh.id,
            advisor_id=advisor.id,
        ),
        m.User(
            email="priya.patel@nexgile.demo",
            full_name="Priya Patel",
            hashed_password=hash_password("demo123"),
            role="CLIENT",
            title="Physician",
            avatar_initials="PP",
            household_id=patel_hh.id,
            advisor_id=advisor.id,
        ),
    ]
    db.add_all(users)
    db.flush()

    schwab = m.Custodian(name="Charles Schwab", code="SCHW", status="active")
    fidelity = m.Custodian(name="Fidelity", code="FIDO", status="active")
    bnym = m.Custodian(name="BNY Mellon Wealth", code="BNYM", status="active")
    db.add_all([schwab, fidelity, bnym])
    db.flush()

    accounts_spec = [
        dict(
            name="Individual Brokerage",
            account_type="brokerage",
            account_number_masked="•••• 4821",
            tax_status="taxable",
            cash_balance=87420,
            owner_name="Alex Morgan",
            custodian_id=schwab.id,
            provider="schwab",
        ),
        dict(
            name="Helios Dynamics 401(k)",
            account_type="401k",
            account_number_masked="•••• 9014",
            tax_status="tax-deferred",
            cash_balance=12400,
            owner_name="Alex Morgan",
            custodian_id=fidelity.id,
            provider="fidelity",
        ),
        dict(
            name="Roth IRA",
            account_type="roth_ira",
            account_number_masked="•••• 2267",
            tax_status="tax-free",
            cash_balance=4200,
            owner_name="Alex Morgan",
            custodian_id=schwab.id,
            provider="schwab",
        ),
        dict(
            name="Traditional IRA",
            account_type="traditional_ira",
            account_number_masked="•••• 5591",
            tax_status="tax-deferred",
            cash_balance=3100,
            owner_name="Alex Morgan",
            custodian_id=schwab.id,
            provider="schwab",
        ),
        dict(
            name="Morgan Family Revocable Trust",
            account_type="trust",
            account_number_masked="•••• 7730",
            tax_status="trust",
            cash_balance=18600,
            owner_name="Morgan Family Trust",
            custodian_id=bnym.id,
            provider="bny_mellon",
            currency="INR",
        ),
        dict(
            name="Cash Reserve",
            account_type="cash",
            account_number_masked="•••• 1102",
            tax_status="taxable",
            cash_balance=185000,
            owner_name="Alex & Jordan Morgan",
            custodian_id=schwab.id,
            provider="schwab",
        ),
    ]
    accounts = []
    for spec in accounts_spec:
        acct = m.Account(
            household_id=household.id,
            as_of=AS_OF,
            source="custodian",
            version=1,
            source_record_id=f"ACCT-{spec['account_type']}-morgan",
            data_quality_status="FRESH",
            updated_at=datetime.utcnow() - timedelta(minutes=5),
            **spec,
        )
        db.add(acct)
        accounts.append(acct)
    db.flush()
    brokerage = next(a for a in accounts if a.account_type == "brokerage")
    k401 = next(a for a in accounts if a.account_type == "401k")
    roth = next(a for a in accounts if a.account_type == "roth_ira")
    ira = next(a for a in accounts if a.account_type == "traditional_ira")
    trust = next(a for a in accounts if a.account_type == "trust")
    cash_acct = next(a for a in accounts if a.account_type == "cash")

    holdings_rows = [
        (brokerage.id, "AAPL", "Apple Inc.", "Equities", "Technology", "US", 850, 228.40, 120785, 0.42, 18.4),
        (brokerage.id, "MSFT", "Microsoft Corp.", "Equities", "Technology", "US", 420, 431.20, 120750, 0.18, 14.2),
        (brokerage.id, "NVDA", "NVIDIA Corp.", "Equities", "Technology", "US", 310, 124.80, 14942, 1.12, 42.6),
        (brokerage.id, "GOOGL", "Alphabet Inc. Class A", "Equities", "Technology", "US", 280, 168.90, 31472, -0.35, 12.1),
        (brokerage.id, "AMZN", "Amazon.com Inc.", "Equities", "Consumer Discretionary", "US", 190, 191.50, 24320, 0.22, 9.8),
        (brokerage.id, "VTI", "Vanguard Total Stock Market ETF", "Equities", "Blend", "US", 980, 286.15, 194432, 0.31, 16.4),
        (brokerage.id, "VOO", "Vanguard S&P 500 ETF", "Equities", "Blend", "US", 640, 548.30, 250880, 0.28, 15.9),
        (brokerage.id, "BND", "Vanguard Total Bond Market ETF", "Fixed Income", "Bonds", "US", 2100, 73.85, 164220, -0.12, 1.4),
        (brokerage.id, "INTC", "Intel Corp.", "Equities", "Technology", "US", 400, 22.40, 16800, -0.84, -18.2),
        (brokerage.id, "NKE", "Nike Inc.", "Equities", "Consumer Discretionary", "US", 180, 78.50, 20160, -0.41, -11.6),
        (k401.id, "FXAIX", "Fidelity 500 Index Fund", "Equities", "Blend", "US", 1850, 218.40, 312400, 0.26, 15.2),
        (k401.id, "FXNAX", "Fidelity U.S. Bond Index", "Fixed Income", "Bonds", "US", 4200, 10.84, 47880, -0.08, 1.1),
        (k401.id, "FSMAX", "Fidelity Extended Market Index", "Equities", "Blend", "US", 980, 92.10, 72400, 0.44, 11.8),
        (k401.id, "FTIHX", "Fidelity Total International Index", "Equities", "International", "Intl", 3100, 14.62, 41200, 0.19, 8.4),
        (roth.id, "VTI", "Vanguard Total Stock Market ETF", "Equities", "Blend", "US", 420, 286.15, 86400, 0.31, 16.4),
        (roth.id, "VXUS", "Vanguard Total International Stock", "Equities", "International", "Intl", 1100, 64.20, 61200, 0.17, 8.1),
        (roth.id, "VNQ", "Vanguard Real Estate ETF", "Alternatives", "Real Estate", "US", 280, 92.40, 23800, 0.09, 4.6),
        (ira.id, "VTI", "Vanguard Total Stock Market ETF", "Equities", "Blend", "US", 210, 286.15, 41200, 0.31, 16.4),
        (ira.id, "BND", "Vanguard Total Bond Market ETF", "Fixed Income", "Bonds", "US", 800, 73.85, 61200, -0.12, 1.4),
        (trust.id, "VOO", "Vanguard S&P 500 ETF", "Equities", "Blend", "US", 380, 548.30, 168400, 0.28, 15.9),
        (trust.id, "BND", "Vanguard Total Bond Market ETF", "Fixed Income", "Bonds", "US", 1600, 73.85, 124800, -0.12, 1.4),
        (trust.id, "VNQ", "Vanguard Real Estate ETF", "Alternatives", "Real Estate", "US", 420, 92.40, 36100, 0.09, 4.6),
        (trust.id, "GLD", "SPDR Gold Shares", "Alternatives", "Commodities", "Global", 210, 248.60, 41200, 0.55, 21.3),
        (cash_acct.id, "SGOV", "iShares 0-3 Month Treasury", "Cash", "Cash", "US", 1640, 100.42, 164600, 0.01, 3.9),
    ]

    holding_objs = []
    for row in holdings_rows:
        acct_id, symbol, name, asset, sector, region, qty, price, cost, day, ytd = row
        h = m.Holding(
            account_id=acct_id,
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
            source_record_id=f"POS-{symbol}-{acct_id}",
            data_quality_status="FRESH",
            version=12,
            updated_at=datetime.utcnow() - timedelta(minutes=5),
        )
        db.add(h)
        holding_objs.append(h)
    db.flush()

    for h in holding_objs:
        if h.quantity <= 1:
            continue
        db.add(
            m.TaxLot(
                holding_id=h.id,
                acquired_on=date(2021, 3, 18),
                quantity=round(h.quantity * 0.55, 4),
                cost_per_share=round((h.cost_basis / h.quantity) * 0.92, 4),
                term="long",
            )
        )
        db.add(
            m.TaxLot(
                holding_id=h.id,
                acquired_on=date(2024, 11, 6),
                quantity=round(h.quantity * 0.45, 4),
                cost_per_share=round((h.cost_basis / h.quantity) * 1.1, 4),
                term="short" if h.symbol in {"INTC", "NKE"} else "long",
            )
        )

    account_totals = {}
    for h in holding_objs:
        mv = h.quantity * h.price
        account_totals.setdefault(h.account_id, {"mv": 0, "cb": 0})
        account_totals[h.account_id]["mv"] += mv
        account_totals[h.account_id]["cb"] += h.cost_basis
    for acct in accounts:
        totals = account_totals.get(acct.id, {"mv": 0, "cb": 0})
        acct.market_value = round(totals["mv"], 2)
        acct.cost_basis = round(totals["cb"], 2)

    residence = m.Account(
        household_id=household.id,
        name="Primary Residence — Pacific Heights",
        account_type="real_estate",
        account_number_masked="Off-book",
        tax_status="personal",
        cash_balance=0,
        market_value=1250000,
        cost_basis=890000,
        owner_name="Alex & Jordan Morgan",
        as_of=AS_OF,
        source="client_statement",
        provider="internal",
        source_record_id="RE-MORGAN-1",
        data_quality_status="STALE",
        version=1,
    )
    mortgage = m.Account(
        household_id=household.id,
        name="First mortgage",
        account_type="liability",
        account_number_masked="•••• 4402",
        tax_status="liability",
        cash_balance=0,
        market_value=780000,
        cost_basis=780000,
        owner_name="Alex & Jordan Morgan",
        as_of=AS_OF,
        source="servicer",
        provider="internal",
        source_record_id="MTG-MORGAN-1",
        data_quality_status="STALE",
        version=1,
    )
    db.add_all([residence, mortgage])

    txns = [
        (brokerage.id, "contribution", "", "ACH contribution — September", 8500, 0, date(2026, 9, 2), "Alex Morgan"),
        (brokerage.id, "trade", "NVDA", "Buy 40 NVDA", -4992, 40, date(2026, 9, 4), "Trading desk"),
        (brokerage.id, "rebalance", "BND", "Trim BND overweight", 7400, -100, date(2026, 8, 21), "Advisor"),
        (k401.id, "contribution", "FXAIX", "Payroll deferral + match", 4200, 0, date(2026, 8, 29), "Payroll"),
        (roth.id, "contribution", "VTI", "Annual Roth contribution", 7000, 24.4, date(2026, 4, 10), "Alex Morgan"),
        (trust.id, "document", "", "Trust restatement uploaded", 0, 0, date(2026, 8, 14), "Estate counsel"),
        (brokerage.id, "message", "", "Advisor note: Q3 review scheduled", 0, 0, date(2026, 9, 5), "Sarah Wilson"),
        (cash_acct.id, "transfer", "SGOV", "Sweep excess cash to T-bills", 25000, 249, date(2026, 8, 28), "Treasury"),
    ]
    for acct_id, ttype, symbol, desc, amount, qty, occurred, actor in txns:
        db.add(
            m.Transaction(
                account_id=acct_id,
                txn_type=ttype,
                symbol=symbol,
                description=desc,
                amount=amount,
                quantity=qty,
                occurred_on=occurred,
                actor=actor,
            )
        )

    bench = m.Benchmark(name="60/40 Global Blend", code="NXG-60-40", ytd_return_pct=11.4, one_year_return_pct=14.8)
    db.add(bench)
    db.flush()

    portfolio = m.Portfolio(
        household_id=household.id,
        name="Morgan Family Master Portfolio",
        strategy="Moderate Growth — Tax Aware",
        risk_score=64,
        target_equity=0.62,
        target_fixed_income=0.22,
        target_alternatives=0.08,
        target_cash=0.06,
        target_other=0.02,
        benchmark_id=bench.id,
        as_of=AS_OF,
        version=3,
    )
    db.add(portfolio)
    db.flush()
    db.add_all(
        [
            m.Allocation(portfolio_id=portfolio.id, asset_class="Equities", current_pct=0.68, target_pct=0.62),
            m.Allocation(portfolio_id=portfolio.id, asset_class="Fixed Income", current_pct=0.18, target_pct=0.22),
            m.Allocation(portfolio_id=portfolio.id, asset_class="Alternatives", current_pct=0.08, target_pct=0.08),
            m.Allocation(portfolio_id=portfolio.id, asset_class="Cash", current_pct=0.06, target_pct=0.06),
        ]
    )

    total_mv = sum(a.market_value for a in accounts)
    start = total_mv / 1.132
    for i in range(13):
        d = date(2025, 9, 1) + timedelta(days=30 * i)
        if d > AS_OF:
            d = AS_OF
        progress = i / 12
        noise = [0, 0.012, -0.008, 0.021, 0.006, -0.014, 0.018, 0.009, -0.004, 0.016, 0.011, 0.007, 0.004][i]
        value = start * (1 + 0.132 * progress + noise)
        bench_v = start * (1 + 0.114 * progress + noise * 0.7)
        db.add(m.PerformancePoint(portfolio_id=portfolio.id, as_of=d, market_value=round(value, 2), benchmark_value=round(bench_v, 2)))

    goals = [
        m.Goal(
            household_id=household.id,
            name="Retirement — Independent lifestyle",
            category="Retirement",
            target_amount=3000000,
            current_amount=2140000,
            target_date=date(2041, 6, 1),
            probability=0.84,
            projected_status="On Track",
            linked_accounts=["Helios Dynamics 401(k)", "Roth IRA", "Individual Brokerage"],
            annual_contribution=62000,
            notes="Target spending ₹2,10,000 in today's rupees, age 62.",
        ),
        m.Goal(
            household_id=household.id,
            name="Education — Cameron & Avery",
            category="Education",
            target_amount=250000,
            current_amount=170000,
            target_date=date(2032, 8, 1),
            probability=0.78,
            projected_status="Watch",
            linked_accounts=["529 Plan (external)", "Brokerage sleeve"],
            annual_contribution=18000,
            notes="Two children, private university assumption.",
        ),
        m.Goal(
            household_id=household.id,
            name="Legacy & family capital",
            category="Legacy",
            target_amount=1500000,
            current_amount=620000,
            target_date=date(2048, 1, 1),
            probability=0.61,
            projected_status="Needs Attention",
            linked_accounts=["Morgan Family Revocable Trust"],
            annual_contribution=25000,
            notes="Funded via trust growth and surplus cash flow.",
        ),
        m.Goal(
            household_id=household.id,
            name="Lake Tahoe residence",
            category="Major Purchase",
            target_amount=150000,
            current_amount=98000,
            target_date=date(2028, 5, 1),
            probability=0.91,
            projected_status="On Track",
            linked_accounts=["Cash Reserve"],
            annual_contribution=24000,
            notes="Down payment supplement; primary mortgage not in book.",
        ),
    ]
    db.add_all(goals)
    db.flush()

    for g in goals:
        db.add_all(
            [
                m.Scenario(goal_id=g.id, name="Base Case", growth_rate=0.065, projected_value=round(g.current_amount * 1.065 ** max(1, (g.target_date.year - 2026)), 0), probability=g.probability, isolated=True),
                m.Scenario(goal_id=g.id, name="Optimistic", growth_rate=0.09, contribution_change=0.15, projected_value=round(g.current_amount * 1.09 ** max(1, (g.target_date.year - 2026)) * 1.12, 0), probability=min(0.97, g.probability + 0.1), isolated=True),
                m.Scenario(goal_id=g.id, name="Conservative", growth_rate=0.035, contribution_change=-0.1, projected_value=round(g.current_amount * 1.035 ** max(1, (g.target_date.year - 2026)) * 0.92, 0), probability=max(0.35, g.probability - 0.18), isolated=True),
            ]
        )

    db.add_all(
        [
            m.Recommendation(household_id=household.id, category="allocation", title="Technology overweight vs policy", body="Technology exposure is above the 28% target sleeve. Consider trimming concentrated names into VTI/VOO on strength.", severity="warning"),
            m.Recommendation(household_id=household.id, category="tax", title="Tax-loss harvesting opportunity", body="INTC, NKE, and a portion of BND lots are eligible for harvest with no open wash-sale window.", severity="opportunity"),
            m.Recommendation(household_id=household.id, category="goals", title="Retirement goal 71% funded", body="Retirement capital is 71% of the ₹30,00,000 target with an 84% simulated success rate under the base case.", severity="info"),
            m.Recommendation(household_id=household.id, category="estate", title="Healthcare directive review due", body="Advance healthcare directive last reviewed 18 months ago. Counsel recommends a 2026 refresh.", severity="warning"),
        ]
    )

    db.add_all(
        [
            m.TaxOpportunity(household_id=household.id, opportunity_type="tlh", title="Tax-loss harvesting", detail="Harvest INTC, NKE, and selected BND lots. Estimated federal benefit at 37% + 3.8% NIIT.", estimated_benefit=12840, status="identified"),
            m.TaxOpportunity(household_id=household.id, opportunity_type="gains_budget", title="Capital gains budget remaining", detail="₹42,600 remaining in the 2026 long-term gains budget before crossing the next NIIT threshold.", estimated_benefit=0, status="monitor"),
            m.TaxOpportunity(household_id=household.id, opportunity_type="roth", title="Roth conversion window", detail="Partial conversion of ₹48,000 from the 401(k) rollover sleeve while MAGI remains below the next IRMAA cliff.", estimated_benefit=6400, status="proposed"),
            m.TaxOpportunity(household_id=household.id, opportunity_type="rmd", title="RMD not yet required", detail="Alex (age 47) has no RMD. First projected RMD year is 2052. QCDs become available at 70½ for charitable plan.", estimated_benefit=0, status="informational"),
        ]
    )

    holding_by_symbol = {}
    for h in holding_objs:
        holding_by_symbol.setdefault(h.symbol, h)
    db.add_all(
        [
            m.Harvest(household_id=household.id, holding_id=holding_by_symbol.get("INTC").id if holding_by_symbol.get("INTC") else None, symbol="INTC", security_name="Intel Corp.", unrealized_loss=-7840, potential_tax_benefit=3199, wash_sale_status="Clear", replacement_security="SOXX", status="proposed"),
            m.Harvest(household_id=household.id, holding_id=holding_by_symbol.get("NKE").id if holding_by_symbol.get("NKE") else None, symbol="NKE", security_name="Nike Inc.", unrealized_loss=-6030, potential_tax_benefit=2460, wash_sale_status="Clear", replacement_security="XLY", status="proposed"),
            m.Harvest(household_id=household.id, holding_id=holding_by_symbol.get("BND").id if holding_by_symbol.get("BND") else None, symbol="BND", security_name="Vanguard Total Bond Market ETF", unrealized_loss=-9135, potential_tax_benefit=3727, wash_sale_status="30-day watch", replacement_security="AGG", status="review"),
        ]
    )
    db.add(m.WashSaleWindow(household_id=household.id, symbol="BND", window_start=date(2026, 8, 21), window_end=date(2026, 9, 20), restricted=True))
    db.add(
        m.RMD(
            household_id=household.id,
            account_name="Helios Dynamics 401(k)",
            required_amount=0,
            taken_ytd=0,
            remaining=0,
            deadline=date(2052, 12, 31),
            status="not_required",
        )
    )

    db.add(m.Charity(name="Bay Area Education Fund", ein="94-0000001", mission="Expand access to STEM education."))
    db.add(m.Charity(name="Coastal Conservancy Trust", ein="94-0000002", mission="Protect California shoreline ecosystems."))
    db.add(
        m.DAF(
            household_id=household.id,
            name="Morgan Family Donor-Advised Fund",
            balance=86400,
            ytd_grants=22000,
            sponsor="Fidelity Charitable",
        )
    )
    db.add_all(
        [
            m.Gift(household_id=household.id, charity_name="Bay Area Education Fund", gift_type="DAF grant", amount=12000, gifted_on=date(2026, 3, 12), tax_deduction_estimate=0),
            m.Gift(household_id=household.id, charity_name="Coastal Conservancy Trust", gift_type="appreciated securities", amount=18400, gifted_on=date(2026, 6, 4), tax_deduction_estimate=18400),
            m.Gift(household_id=household.id, charity_name="Community Clinic", gift_type="QCD-eligible future", amount=0, gifted_on=date(2026, 1, 1), tax_deduction_estimate=0, status="planned"),
        ]
    )

    db.add(
        m.EstatePlan(
            household_id=household.id,
            will_status="current",
            trust_status="current",
            poa_status="current",
            healthcare_directive_status="review_due",
            last_review=date(2025, 3, 18),
            next_review=date(2026, 10, 15),
            estate_tax_exposure=185000,
            attorney_name="Elena Vasquez, LLP",
            readiness_score=78,
        )
    )
    db.add_all(
        [
            m.Trust(household_id=household.id, name="Morgan Family Revocable Trust", trust_type="Revocable Living", trustee="Alex Morgan / Jordan Morgan", assets=421600, funded=True),
            m.Trust(household_id=household.id, name="Morgan Irrevocable Life Insurance Trust", trust_type="ILIT", trustee="Bay Fiduciary Co.", assets=0, funded=False),
        ]
    )
    db.add_all(
        [
            m.Beneficiary(household_id=household.id, name="Jordan Morgan", relationship="Spouse", account_or_trust="All qualified accounts", share_pct=100, contingent=False, last_reviewed=date(2025, 11, 2)),
            m.Beneficiary(household_id=household.id, name="Cameron Morgan", relationship="Child", account_or_trust="Revocable Trust", share_pct=50, contingent=True, last_reviewed=date(2025, 11, 2)),
            m.Beneficiary(household_id=household.id, name="Avery Morgan", relationship="Child", account_or_trust="Revocable Trust", share_pct=50, contingent=True, last_reviewed=date(2025, 11, 2)),
        ]
    )

    db.add_all(
        [
            m.Document(household_id=household.id, name="2025 Form 1040 — Joint Return", category="Tax", doc_type="PDF", uploaded_on=date(2026, 4, 12), version="1.1", expiry_or_review=date(2027, 4, 15), owner="Alex Morgan", status="current", ai_classification="tax_return"),
            m.Document(household_id=household.id, name="Revocable Trust — Restatement", category="Trust", doc_type="PDF", uploaded_on=date(2026, 8, 14), version="3.0", expiry_or_review=date(2028, 8, 14), owner="Elena Vasquez, LLP", status="current", ai_classification="estate_trust"),
            m.Document(household_id=household.id, name="Last Will and Testament", category="Estate", doc_type="PDF", uploaded_on=date(2025, 3, 18), version="2.0", expiry_or_review=date(2026, 10, 15), owner="Elena Vasquez, LLP", status="review_due", ai_classification="estate_will"),
            m.Document(household_id=household.id, name="Durable Power of Attorney", category="Estate", doc_type="PDF", uploaded_on=date(2025, 3, 18), version="2.0", owner="Elena Vasquez, LLP", status="current", ai_classification="poa"),
            m.Document(household_id=household.id, name="Q2 2026 Brokerage Statement", category="Statements", doc_type="PDF", uploaded_on=date(2026, 7, 8), version="1.0", owner="Charles Schwab", status="current", ai_classification="statement"),
            m.Document(household_id=household.id, name="IPS — Investment Policy Statement", category="Investment", doc_type="PDF", uploaded_on=date(2026, 1, 20), version="2026.1", expiry_or_review=date(2027, 1, 20), owner="Sarah Wilson", status="current", ai_classification="ips"),
            m.Document(household_id=household.id, name="401(k) Summary Plan Description", category="Retirement", doc_type="PDF", uploaded_on=date(2026, 2, 3), version="2026", owner="Helios Dynamics", status="current", ai_classification="spd"),
            m.Document(household_id=household.id, name="Healthcare Directive", category="Estate", doc_type="PDF", uploaded_on=date(2024, 9, 9), version="1.0", expiry_or_review=date(2026, 9, 30), owner="Alex Morgan", status="expiring", ai_classification="healthcare_directive"),
        ]
    )

    db.add_all(
        [
            m.Message(household_id=household.id, sender="Sarah Wilson", sender_role="ADVISOR", subject="Q3 planning meeting — Sep 18", body="Alex and Jordan — I've reserved Thursday 10:00am PT for our Q3 review. Agenda: allocation drift, TLH, and Tahoe down-payment timing.", thread_id="t-q3", read=False),
            m.Message(household_id=household.id, sender="Alex Morgan", sender_role="CLIENT", subject="Re: Charitable grant", body="Please proceed with the ₹12,000 DAF grant to Bay Area Education Fund from the remaining 2026 budget.", thread_id="t-daf", read=True),
            m.Message(household_id=household.id, sender="Operations", sender_role="ADMIN", subject="Statement available", body="Your August brokerage statement is now in the document vault.", thread_id="t-stmt", read=True),
        ]
    )

    db.add(
        m.Meeting(
            household_id=household.id,
            title="Q3 Wealth Review",
            scheduled_for=datetime(2026, 9, 18, 17, 0),
            location="Video — Nexgile Secure Room",
            agenda="Performance, tax opportunities, Tahoe funding, estate directive refresh.",
        )
    )
    db.add_all(
        [
            m.ActionItem(household_id=household.id, title="Approve tax-loss harvest proposal", owner="Alex Morgan", due_on=date(2026, 9, 12), status="open", priority="high"),
            m.ActionItem(household_id=household.id, title="Refresh healthcare directive", owner="Elena Vasquez, LLP", due_on=date(2026, 9, 30), status="open", priority="high"),
            m.ActionItem(household_id=household.id, title="Confirm 2026 charitable remaining budget", owner="Jordan Morgan", due_on=date(2026, 10, 15), status="open", priority="medium"),
            m.ActionItem(household_id=household.id, title="Prepare Q3 performance pack", owner="Sarah Wilson", due_on=date(2026, 9, 16), status="in_progress", priority="high"),
        ]
    )

    plan = m.Plan(
        name="Helios Dynamics 401(k)",
        sponsor_name="Helios Dynamics, Inc.",
        plan_assets=186400000,
        participants=842,
        participation_rate=0.91,
        avg_deferral_rate=0.084,
        employer_match="100% of first 4%",
        vesting="3-year cliff",
        plan_health="healthy",
        fees_bps=38,
        compliance_status="ADP/ACP in cycle",
    )
    db.add(plan)
    db.flush()
    db.add(m.Sponsor(name="Helios Dynamics, Inc.", industry="Enterprise software", plan_id=plan.id, contact_name="Maria Chen"))
    db.add(
        m.Participant(
            plan_id=plan.id,
            name="Priya Shah",
            email="priya.shah@nexgile.demo",
            balance=187400,
            employee_deferral_ytd=14200,
            employer_match_ytd=5680,
            vested_pct=100,
            contribution_rate=0.10,
            retirement_readiness=0.74,
            income_projection=62000,
        )
    )
    db.add(
        m.Participant(
            plan_id=plan.id,
            name="Alex Morgan",
            email="alex.morgan@nexgile.demo",
            balance=687400,
            employee_deferral_ytd=23500,
            employer_match_ytd=9400,
            vested_pct=100,
            contribution_rate=0.12,
            retirement_readiness=0.84,
            income_projection=98000,
        )
    )
    db.add_all(
        [
            m.InvestmentOption(plan_id=plan.id, name="Fidelity 500 Index", ticker="FXAIX", category="U.S. Large Cap", expense_ratio=0.015, ytd_return=15.2),
            m.InvestmentOption(plan_id=plan.id, name="Fidelity U.S. Bond Index", ticker="FXNAX", category="Fixed Income", expense_ratio=0.025, ytd_return=1.1),
            m.InvestmentOption(plan_id=plan.id, name="Fidelity Extended Market", ticker="FSMAX", category="U.S. Mid/Small", expense_ratio=0.035, ytd_return=11.8),
            m.InvestmentOption(plan_id=plan.id, name="Fidelity Total International", ticker="FTIHX", category="International", expense_ratio=0.06, ytd_return=8.4),
            m.InvestmentOption(plan_id=plan.id, name="Target Date 2045", ticker="FDKJX", category="Target Date", expense_ratio=0.12, ytd_return=12.6),
        ]
    )
    db.add_all(
        [
            m.Fee(plan_id=plan.id, fee_type="recordkeeping", amount_bps=18, notes="Per-participant + asset"),
            m.Fee(plan_id=plan.id, fee_type="advisory", amount_bps=12, notes="Nexgile 3(38)"),
            m.Fee(plan_id=plan.id, fee_type="fund_weighted", amount_bps=8, notes="Lineup weighted ER"),
        ]
    )
    db.add_all(
        [
            m.ComplianceTest(plan_id=plan.id, name="ADP Test", year=2025, result="pass", notes="HCE 7.1% / NHCE 6.4%"),
            m.ComplianceTest(plan_id=plan.id, name="ACP Test", year=2025, result="pass"),
            m.ComplianceTest(plan_id=plan.id, name="Top Heavy", year=2025, result="pass"),
            m.ComplianceTest(plan_id=plan.id, name="Form 5500", year=2025, result="filed"),
        ]
    )

    db.add_all(
        [
            m.Report(household_id=household.id, name="Q3 Portfolio Review", report_type="portfolio_review", period="Q3 2026", generated_on=AS_OF, summary="Household invested assets, allocation vs IPS, and activity."),
            m.Report(household_id=household.id, name="Performance Report", report_type="performance", period="YTD 2026", generated_on=AS_OF, summary="Time-weighted return vs 60/40 blend."),
            m.Report(household_id=household.id, name="Tax Summary", report_type="tax_summary", period="2026 YTD", generated_on=AS_OF, summary="Realized/unrealized, harvest candidates, gains budget."),
            m.Report(household_id=household.id, name="Goal Progress", report_type="goal_progress", period="September 2026", generated_on=AS_OF, summary="Funding ratios and scenario fan."),
            m.Report(household_id=household.id, name="Retirement Readiness", report_type="retirement_readiness", period="September 2026", generated_on=AS_OF, summary="Probability of success and income replacement."),
            m.Report(household_id=household.id, name="Household Wealth Report", report_type="household_wealth", period="September 2026", generated_on=AS_OF, summary="Net worth, accounts, liabilities, and liquidity."),
        ]
    )

    db.add_all(
        [
            m.Alert(household_id=household.id, title="Healthcare directive review due", body="Document expires review window on Sep 30, 2026.", severity="warning", category="estate"),
            m.Alert(household_id=household.id, title="TLH candidates identified", body="Three lots eligible. Advisor review required before trade.", severity="opportunity", category="tax"),
            m.Alert(household_id=household.id, title="Q3 meeting in 11 days", body="Sep 18, 10:00am PT — agenda drafted.", severity="info", category="meeting"),
            m.Alert(household_id=household.id, title="Technology overweight", body="Tech sleeve 34% vs 28% policy target.", severity="warning", category="portfolio"),
        ]
    )

    db.add(
        m.Approval(
            household_id=household.id,
            requested_by="Sarah Wilson",
            requested_by_user_id=next((u.id for u in users if u.email == "sarah.wilson@nexgile.demo"), None),
            role="ADVISOR",
            action="tax_harvest",
            entity_type="Harvest",
            entity_id="batch-2026-09",
            old_value={"status": "identified"},
            new_value={"status": "proposed", "symbols": ["INTC", "NKE", "BND"]},
            status="pending",
            notes="Client approval required before sending to trading.",
        )
    )
    db.add(
        m.AuditEvent(
            user="system",
            action="seed",
            entity_type="Household",
            entity_id=str(household.id),
            new_value={"name": "Morgan Family"},
            status="recorded",
        )
    )
    db.add(
        m.ComplianceReview(
            title="Q3 correspondence archive",
            status="open",
            reviewer="Compliance",
            due_on=date(2026, 9, 30),
            notes="Archive advisor messages for SEC books and records.",
        )
    )
    db.add(
        m.LineageRecord(
            entity_type="Portfolio",
            entity_id=str(portfolio.id),
            source="book_of_record",
            provider="internal",
            source_record_id="PORT-MORGAN-1",
            as_of=AS_OF,
            version=3,
            data_quality_status="FRESH",
        )
    )
    db.add(
        m.Rebalance(
            portfolio_id=portfolio.id,
            status="preview",
            estimated_gains=12400,
            estimated_tax=2950,
            approval_required=True,
            payload={"note": "Preview only. Book of record not modified."},
        )
    )
    db.add(
        m.Trade(
            portfolio_id=portfolio.id,
            symbol="BND",
            side="sell",
            quantity=100,
            estimated_amount=7385,
            status="preview",
            book_of_record_impact=False,
        )
    )

    db.flush()
    alex_participant = db.query(m.Participant).filter(m.Participant.email == "alex.morgan@nexgile.demo").first()
    priya_participant = db.query(m.Participant).filter(m.Participant.email == "priya.shah@nexgile.demo").first()
    if alex_participant:
        db.add(m.Contribution(participant_id=alex_participant.id, period="2026-08", employee_amount=2350, employer_amount=940))
    if priya_participant:
        db.add(m.Contribution(participant_id=priya_participant.id, period="2026-08", employee_amount=1420, employer_amount=568))

    seed_other_households(db, advisor, chen_hh, shah_hh, patel_hh, schwab.id, fidelity.id)
    from app.db.seed_ai import seed_ai_layer

    seed_ai_layer(db)
    from app.db.seed_integrations import seed_integrations
    from app.db.convert_inr import apply_inr_book

    seed_integrations(db)
    apply_inr_book(db)

    db.commit()
