from datetime import datetime, date, timezone
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def _now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, index=True)
    title = Column(String(128), default="")
    phone = Column(String(64), default="")
    avatar_initials = Column(String(8), default="")
    is_active = Column(Boolean, default=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=True, index=True)
    advisor_id = Column(Integer, ForeignKey("advisors.id"), nullable=True, index=True)
    first_name = Column(String(128), default="")
    last_name = Column(String(128), default="")
    failed_login_count = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, default=_now)
    email_verified = Column(Boolean, default=True, nullable=False)
    email_verified_at = Column(DateTime, nullable=True)
    terms_accepted_at = Column(DateTime, nullable=True)
    mfa_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)

    household = relationship("Household", back_populates="members", foreign_keys=[household_id])


class Household(Base):
    __tablename__ = "households"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    primary_client_name = Column(String(255))
    risk_profile = Column(String(64), default="Moderate Growth")
    domicile = Column(String(128), default="California, USA")
    tax_filing_status = Column(String(64), default="Married Filing Jointly")
    advisor_id = Column(Integer, ForeignKey("advisors.id"), nullable=True, index=True)
    other_assets = Column(Float, default=0)
    liabilities = Column(Float, default=0)
    emergency_reserve = Column(Float, default=0)
    upcoming_needs = Column(Float, default=0)
    liquidity_label = Column(String(128), default="")
    estimated_tax_liability = Column(Float, default=0)
    capital_gains_budget_used = Column(Float, default=0)
    capital_gains_budget_limit = Column(Float, default=0)
    carryforward_losses = Column(Float, default=0)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    members = relationship("User", back_populates="household", foreign_keys="User.household_id")
    accounts = relationship("Account", back_populates="household")
    goals = relationship("Goal", back_populates="household")


class Advisor(Base):
    __tablename__ = "advisors"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True)
    title = Column(String(128), default="Senior Wealth Advisor")
    team = Column(String(128), default="Private Client Group")
    phone = Column(String(64), default="")
    credentials = Column(String(255), default="CFP®, CFA")
    created_at = Column(DateTime, default=_now)


class Custodian(Base):
    __tablename__ = "custodians"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    code = Column(String(32), unique=True)
    status = Column(String(32), default="active")


class Account(Base):
    __tablename__ = "accounts"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"), index=True)
    custodian_id = Column(Integer, ForeignKey("custodians.id"), nullable=True)
    name = Column(String(255), nullable=False)
    account_type = Column(String(64), nullable=False)
    account_number_masked = Column(String(64))
    tax_status = Column(String(64), default="taxable")
    currency = Column(String(8), default="INR")
    cash_balance = Column(Float, default=0)
    market_value = Column(Float, default=0)
    cost_basis = Column(Float, default=0)
    status = Column(String(32), default="open")
    owner_name = Column(String(255))
    as_of = Column(Date)
    source = Column(String(64), default="custodian")
    provider = Column(String(64), default="schwab")
    source_record_id = Column(String(128), default="")
    received_at = Column(DateTime, default=_now)
    data_quality_status = Column(String(32), default="FRESH")
    version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    household = relationship("Household", back_populates="accounts")
    holdings = relationship("Holding", back_populates="account")


class Holding(Base):
    __tablename__ = "holdings"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), index=True)
    symbol = Column(String(32), index=True)
    name = Column(String(255))
    asset_class = Column(String(64))
    sector = Column(String(64), default="")
    region = Column(String(64), default="US")
    quantity = Column(Float, default=0)
    price = Column(Float, default=0)
    cost_basis = Column(Float, default=0)
    day_change_pct = Column(Float, default=0)
    ytd_return_pct = Column(Float, default=0)
    as_of = Column(Date)
    source = Column(String(64), default="market_data")
    provider = Column(String(64), default="internal_pricing")
    source_record_id = Column(String(128), default="")
    received_at = Column(DateTime, default=_now)
    data_quality_status = Column(String(32), default="FRESH")
    version = Column(Integer, default=1)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    account = relationship("Account", back_populates="holdings")
    tax_lots = relationship("TaxLot", back_populates="holding")


class TaxLot(Base):
    __tablename__ = "tax_lots"
    id = Column(Integer, primary_key=True)
    holding_id = Column(Integer, ForeignKey("holdings.id"))
    acquired_on = Column(Date)
    quantity = Column(Float)
    cost_per_share = Column(Float)
    term = Column(String(16), default="long")
    holding = relationship("Holding", back_populates="tax_lots")


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey("accounts.id"))
    txn_type = Column(String(64))
    symbol = Column(String(32), default="")
    description = Column(String(512))
    amount = Column(Float, default=0)
    quantity = Column(Float, default=0)
    occurred_on = Column(Date)
    status = Column(String(32), default="posted")
    actor = Column(String(128), default="")


class Portfolio(Base):
    __tablename__ = "portfolios"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"), index=True)
    name = Column(String(255), default="Household Portfolio")
    strategy = Column(String(128), default="Moderate Growth")
    risk_score = Column(Float, default=62)
    target_equity = Column(Float, default=0.62)
    target_fixed_income = Column(Float, default=0.22)
    target_alternatives = Column(Float, default=0.08)
    target_cash = Column(Float, default=0.06)
    target_other = Column(Float, default=0.02)
    benchmark_id = Column(Integer, ForeignKey("benchmarks.id"), nullable=True)
    as_of = Column(Date)
    source = Column(String(64), default="book_of_record")
    provider = Column(String(64), default="internal")
    source_record_id = Column(String(128), default="")
    received_at = Column(DateTime, default=_now)
    data_quality_status = Column(String(32), default="FRESH")
    version = Column(Integer, default=3)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class Allocation(Base):
    __tablename__ = "allocations"
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    asset_class = Column(String(64))
    current_pct = Column(Float)
    target_pct = Column(Float)


class Benchmark(Base):
    __tablename__ = "benchmarks"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    code = Column(String(32))
    ytd_return_pct = Column(Float, default=0)
    one_year_return_pct = Column(Float, default=0)


class PerformancePoint(Base):
    __tablename__ = "performance_points"
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    as_of = Column(Date)
    market_value = Column(Float)
    benchmark_value = Column(Float)


class Goal(Base):
    __tablename__ = "goals"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"), index=True)
    name = Column(String(255))
    category = Column(String(64))
    target_amount = Column(Float)
    current_amount = Column(Float)
    target_date = Column(Date)
    probability = Column(Float, default=0)
    projected_status = Column(String(64), default="On Track")
    linked_accounts = Column(JSON, default=list)
    annual_contribution = Column(Float, default=0)
    notes = Column(Text, default="")
    household = relationship("Household", back_populates="goals")


class Scenario(Base):
    __tablename__ = "scenarios"
    id = Column(Integer, primary_key=True)
    goal_id = Column(Integer, ForeignKey("goals.id"))
    name = Column(String(64))
    growth_rate = Column(Float)
    contribution_change = Column(Float, default=0)
    projected_value = Column(Float)
    probability = Column(Float)
    isolated = Column(Boolean, default=True)


class Recommendation(Base):
    __tablename__ = "recommendations"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    category = Column(String(64))
    title = Column(String(255))
    body = Column(Text)
    severity = Column(String(32), default="info")
    advisor_review = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)


class TaxOpportunity(Base):
    __tablename__ = "tax_opportunities"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    opportunity_type = Column(String(64))
    title = Column(String(255))
    detail = Column(Text)
    estimated_benefit = Column(Float, default=0)
    status = Column(String(32), default="identified")
    requires_approval = Column(Boolean, default=True)


class Harvest(Base):
    __tablename__ = "harvests"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    holding_id = Column(Integer, ForeignKey("holdings.id"), nullable=True)
    symbol = Column(String(32))
    security_name = Column(String(255))
    unrealized_loss = Column(Float)
    potential_tax_benefit = Column(Float)
    wash_sale_status = Column(String(64))
    replacement_security = Column(String(64))
    status = Column(String(32), default="proposed")
    tax_rate_assumed = Column(Float, default=0.37)


class WashSaleWindow(Base):
    __tablename__ = "wash_sale_windows"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=True, index=True)
    symbol = Column(String(32))
    window_start = Column(Date)
    window_end = Column(Date)
    restricted = Column(Boolean, default=False)


class RMD(Base):
    __tablename__ = "rmds"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    account_name = Column(String(255))
    required_amount = Column(Float)
    taken_ytd = Column(Float, default=0)
    remaining = Column(Float)
    deadline = Column(Date)
    status = Column(String(32), default="not_required")


class Charity(Base):
    __tablename__ = "charities"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    ein = Column(String(32))
    mission = Column(Text, default="")


class DAF(Base):
    __tablename__ = "dafs"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    name = Column(String(255))
    balance = Column(Float)
    ytd_grants = Column(Float, default=0)
    sponsor = Column(String(255), default="Fidelity Charitable")


class Gift(Base):
    __tablename__ = "gifts"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    charity_name = Column(String(255))
    gift_type = Column(String(64))
    amount = Column(Float)
    gifted_on = Column(Date)
    tax_deduction_estimate = Column(Float)
    status = Column(String(32), default="completed")


class EstatePlan(Base):
    __tablename__ = "estate_plans"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    will_status = Column(String(32), default="current")
    trust_status = Column(String(32), default="current")
    poa_status = Column(String(32), default="current")
    healthcare_directive_status = Column(String(32), default="review_due")
    last_review = Column(Date)
    next_review = Column(Date)
    estate_tax_exposure = Column(Float, default=0)
    attorney_name = Column(String(255), default="")
    readiness_score = Column(Float, default=0)


class Trust(Base):
    __tablename__ = "trusts"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    name = Column(String(255))
    trust_type = Column(String(64))
    trustee = Column(String(255))
    assets = Column(Float)
    funded = Column(Boolean, default=True)


class Beneficiary(Base):
    __tablename__ = "beneficiaries"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    name = Column(String(255))
    relationship = Column(String(64))
    account_or_trust = Column(String(255))
    share_pct = Column(Float)
    contingent = Column(Boolean, default=False)
    last_reviewed = Column(Date)


class DistributionRequest(Base):
    __tablename__ = "distribution_requests"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    account_name = Column(String(255))
    amount = Column(Float)
    reason = Column(String(255))
    status = Column(String(32), default="pending")
    requested_on = Column(Date)


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"), index=True)
    name = Column(String(255))
    category = Column(String(64))
    doc_type = Column(String(64))
    uploaded_on = Column(Date)
    version = Column(String(16), default="1.0")
    expiry_or_review = Column(Date, nullable=True)
    owner = Column(String(255))
    status = Column(String(32), default="current")
    ai_classification = Column(String(128), default="")
    file_path = Column(String(512), default="")
    source = Column(String(64), default="document_vault")


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    sender = Column(String(255))
    sender_role = Column(String(32))
    subject = Column(String(255))
    body = Column(Text)
    created_at = Column(DateTime, default=_now)
    read = Column(Boolean, default=False)
    thread_id = Column(String(64), default="")


class Meeting(Base):
    __tablename__ = "meetings"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    title = Column(String(255))
    scheduled_for = Column(DateTime)
    location = Column(String(255), default="Video")
    agenda = Column(Text, default="")
    status = Column(String(32), default="scheduled")


class ActionItem(Base):
    __tablename__ = "action_items"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=True)
    title = Column(String(255))
    owner = Column(String(255))
    due_on = Column(Date)
    status = Column(String(32), default="open")
    priority = Column(String(16), default="medium")


class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    sponsor_name = Column(String(255))
    plan_assets = Column(Float)
    participants = Column(Integer)
    participation_rate = Column(Float)
    avg_deferral_rate = Column(Float)
    employer_match = Column(String(128))
    vesting = Column(String(128))
    plan_health = Column(String(32), default="healthy")
    fees_bps = Column(Float, default=42)
    compliance_status = Column(String(64), default="in_cycle")


class Sponsor(Base):
    __tablename__ = "sponsors"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    industry = Column(String(128))
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=True)
    contact_name = Column(String(255))


class Participant(Base):
    __tablename__ = "participants"
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("plans.id"))
    name = Column(String(255))
    email = Column(String(255))
    balance = Column(Float)
    employee_deferral_ytd = Column(Float)
    employer_match_ytd = Column(Float)
    vested_pct = Column(Float)
    contribution_rate = Column(Float)
    retirement_readiness = Column(Float)
    income_projection = Column(Float)


class Contribution(Base):
    __tablename__ = "contributions"
    id = Column(Integer, primary_key=True)
    participant_id = Column(Integer, ForeignKey("participants.id"))
    period = Column(String(32))
    employee_amount = Column(Float)
    employer_amount = Column(Float)


class InvestmentOption(Base):
    __tablename__ = "investment_options"
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("plans.id"))
    name = Column(String(255))
    ticker = Column(String(32))
    category = Column(String(64))
    expense_ratio = Column(Float)
    ytd_return = Column(Float)


class Fee(Base):
    __tablename__ = "fees"
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("plans.id"))
    fee_type = Column(String(64))
    amount_bps = Column(Float)
    notes = Column(String(255), default="")


class ComplianceTest(Base):
    __tablename__ = "compliance_tests"
    id = Column(Integer, primary_key=True)
    plan_id = Column(Integer, ForeignKey("plans.id"))
    name = Column(String(128))
    year = Column(Integer)
    result = Column(String(32))
    notes = Column(String(255), default="")


class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    symbol = Column(String(32))
    side = Column(String(8))
    quantity = Column(Float)
    estimated_amount = Column(Float)
    status = Column(String(32), default="preview")
    book_of_record_impact = Column(Boolean, default=False)


class Rebalance(Base):
    __tablename__ = "rebalances"
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"))
    created_at = Column(DateTime, default=_now)
    status = Column(String(32), default="preview")
    estimated_gains = Column(Float, default=0)
    estimated_tax = Column(Float, default=0)
    approval_required = Column(Boolean, default=True)
    payload = Column(JSON, default=dict)


class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"))
    name = Column(String(255))
    report_type = Column(String(64))
    period = Column(String(64))
    generated_on = Column(Date)
    status = Column(String(32), default="ready")
    summary = Column(Text, default="")


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=True)
    title = Column(String(255))
    body = Column(Text, default="")
    severity = Column(String(32), default="info")
    category = Column(String(64), default="general")
    created_at = Column(DateTime, default=_now)
    read = Column(Boolean, default=False)


class Approval(Base):
    __tablename__ = "approvals"
    id = Column(Integer, primary_key=True)
    household_id = Column(Integer, ForeignKey("households.id"), nullable=True, index=True)
    requested_by = Column(String(255))
    requested_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role = Column(String(32))
    action = Column(String(128))
    entity_type = Column(String(64))
    entity_id = Column(String(64))
    old_value = Column(JSON, default=dict)
    new_value = Column(JSON, default=dict)
    status = Column(String(32), default="pending")
    version = Column(Integer, default=1)
    idempotency_key = Column(String(128), unique=True, nullable=True)
    created_at = Column(DateTime, default=_now)
    decided_at = Column(DateTime, nullable=True)
    decided_by = Column(String(255), nullable=True)
    notes = Column(Text, default="")


class ComplianceReview(Base):
    __tablename__ = "compliance_reviews"
    id = Column(Integer, primary_key=True)
    title = Column(String(255))
    status = Column(String(32), default="open")
    reviewer = Column(String(255))
    due_on = Column(Date)
    notes = Column(Text, default="")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(Integer, primary_key=True)
    user = Column(String(255))
    actor_role = Column(String(32), default="")
    action = Column(String(128), index=True)
    entity_type = Column(String(64), index=True)
    entity_id = Column(String(64), default="")
    old_value = Column(JSON, default=dict)
    new_value = Column(JSON, default=dict)
    status = Column(String(32), default="recorded")
    result = Column(String(32), default="recorded")
    reason = Column(Text, default="")
    request_id = Column(String(64), default="", index=True)
    timestamp = Column(DateTime, default=_now, index=True)
    ip_address = Column(String(64), default="")


class LineageRecord(Base):
    __tablename__ = "lineage_records"
    id = Column(Integer, primary_key=True)
    entity_type = Column(String(64))
    entity_id = Column(String(64))
    source = Column(String(64))
    provider = Column(String(64))
    source_record_id = Column(String(128), default="")
    as_of = Column(Date)
    received_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now)
    version = Column(Integer, default=1)
    data_quality_status = Column(String(32), default="FRESH")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False)
    jti = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    replaced_by_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=_now)
    ip_address = Column(String(64), default="")
    user_agent = Column(String(255), default="")


class AuthToken(Base):
    """Hashed one-time tokens for email verification and password reset."""
    __tablename__ = "auth_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    purpose = Column(String(32), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False)
    otp_hash = Column(String(128), default="")
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)
    request_id = Column(String(64), default="")
    created_at = Column(DateTime, default=_now)
    __table_args__ = (Index("ix_auth_tokens_user_purpose", "user_id", "purpose"),)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    id = Column(Integer, primary_key=True)
    key = Column(String(128), unique=True, nullable=False)
    user_id = Column(Integer, nullable=True, index=True)
    method = Column(String(16))
    path = Column(String(255))
    response_json = Column(JSON, default=dict)
    status_code = Column(Integer, default=200)
    created_at = Column(DateTime, default=_now)


class JobRun(Base):
    __tablename__ = "job_runs"
    id = Column(Integer, primary_key=True)
    job_name = Column(String(128), index=True)
    idempotency_key = Column(String(128), unique=True, nullable=False)
    status = Column(String(32), default="pending", index=True)
    attempt = Column(Integer, default=0)
    max_attempts = Column(Integer, default=5)
    last_error = Column(Text, default="")
    payload = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)
    version = Column(String(32), nullable=False, default="v1")
    template = Column(Text, nullable=False)
    description = Column(String(255), default="")
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_now)
    __table_args__ = (UniqueConstraint("name", "version", name="uq_prompt_name_version"),)


class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True, nullable=False)
    household_id = Column(Integer, ForeignKey("households.id"), index=True, nullable=False)
    version = Column(String(16), default="1.0")
    storage_key = Column(String(512), default="")
    extracted_text = Column(Text, default="")
    extractor = Column(String(64), default="metadata")
    created_at = Column(DateTime, default=_now)


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id"), index=True, nullable=False)
    household_id = Column(Integer, ForeignKey("households.id"), index=True, nullable=False)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=True)
    chunk_index = Column(Integer, default=0)
    text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    embedding = Column(JSON, default=list)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=_now)


class AIInteraction(Base):
    __tablename__ = "ai_interactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    user_email = Column(String(255), default="")
    actor_role = Column(String(32), default="")
    household_id = Column(Integer, nullable=True, index=True)
    intent = Column(String(64), default="")
    provider = Column(String(32), default="deterministic")
    model = Column(String(64), default="")
    prompt_name = Column(String(128), default="")
    prompt_version = Column(String(32), default="")
    data_scope = Column(JSON, default=dict)
    document_source_ids = Column(JSON, default=list)
    response_status = Column(String(32), default="success")
    request_id = Column(String(64), default="", index=True)
    duration_ms = Column(Float, default=0)
    retrieval_count = Column(Integer, default=0)
    source_count = Column(Integer, default=0)
    token_usage = Column(JSON, default=dict)
    refused = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_now)


class IntegrationConnection(Base):
    __tablename__ = "integration_connections"
    id = Column(Integer, primary_key=True)
    provider_key = Column(String(64), unique=True, nullable=False, index=True)
    display_name = Column(String(128), nullable=False)
    category = Column(String(32), nullable=False, index=True)
    status = Column(String(32), default="mock")
    live = Column(Boolean, default=False)
    last_success_at = Column(DateTime, nullable=True)
    last_error = Column(String(255), default="")
    last_request_id = Column(String(64), default="")
    freshness = Column(String(32), default="unknown")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)


class IntegrationSyncRun(Base):
    __tablename__ = "integration_sync_runs"
    id = Column(Integer, primary_key=True)
    provider_key = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), default="mixed")
    started_at = Column(DateTime, default=_now)
    finished_at = Column(DateTime, nullable=True)
    records_received = Column(Integer, default=0)
    created_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    skipped_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    status = Column(String(32), default="running", index=True)
    error = Column(String(255), default="")
    request_id = Column(String(64), default="", index=True)
    correlation_id = Column(String(64), default="", index=True)
    job_run_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_now)


class IntegrationRecordLink(Base):
    __tablename__ = "integration_record_links"
    id = Column(Integer, primary_key=True)
    provider_key = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False)
    external_id = Column(String(128), nullable=False)
    internal_id = Column(Integer, nullable=True)
    household_id = Column(Integer, nullable=True, index=True)
    last_sync_run_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
    __table_args__ = (UniqueConstraint("provider_key", "entity_type", "external_id", name="uq_integ_link"),)


class ReconciliationException(Base):
    __tablename__ = "reconciliation_exceptions"
    id = Column(Integer, primary_key=True)
    provider_key = Column(String(64), nullable=False, index=True)
    exception_type = Column(String(64), nullable=False)
    entity_type = Column(String(64), default="")
    household_id = Column(Integer, nullable=True, index=True)
    external_id = Column(String(128), default="")
    detail = Column(JSON, default=dict)
    status = Column(String(32), default="open", index=True)
    severity = Column(String(16), default="info")
    request_id = Column(String(64), default="")
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
