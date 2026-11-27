from app.integrations.providers import (
    BusinessProvider,
    CommunicationProvider,
    DocumentProvider,
    FinancialProvider,
    IdentityProvider,
    RetirementProvider,
)

PROVIDER_SPECS = [
    ("custodian", "Custodian Feed", "financial", FinancialProvider),
    ("bank", "Bank / Account Aggregation", "financial", FinancialProvider),
    ("account_aggregation", "Account Aggregation", "financial", FinancialProvider),
    ("broker_dealer", "Broker/Dealer OMS", "financial", FinancialProvider),
    ("market_pricing", "Market / Pricing Data", "financial", FinancialProvider),
    ("alternatives", "Alternatives Admin", "financial", FinancialProvider),
    ("crm", "Wealth CRM", "business", BusinessProvider),
    ("financial_planning", "Financial Planning", "business", BusinessProvider),
    ("tax_preparation", "Tax Preparation", "business", BusinessProvider),
    ("estate_trust", "Estate / Trust", "business", BusinessProvider),
    ("recordkeeper", "Recordkeeper", "retirement", RetirementProvider),
    ("payroll", "Payroll", "retirement", RetirementProvider),
    ("fund_data", "Fund Data", "retirement", RetirementProvider),
    ("morningstar", "Morningstar Fund Data", "retirement", RetirementProvider),
    ("form_5500", "Form 5500", "retirement", RetirementProvider),
    ("dol_irs", "DOL / IRS Feeds", "retirement", RetirementProvider),
    ("email", "Email", "communication", CommunicationProvider),
    ("sms", "SMS", "communication", CommunicationProvider),
    ("push", "Push", "communication", CommunicationProvider),
    ("calendar", "Calendar", "communication", CommunicationProvider),
    ("video", "Video", "communication", CommunicationProvider),
    ("messaging", "Email / SMS / Push", "communication", CommunicationProvider),
    ("identity_sso", "SSO / Identity Provider", "identity", IdentityProvider),
    ("esignature", "E-signature", "documents", DocumentProvider),
    ("compliance_archive", "Compliance Archive", "documents", DocumentProvider),
]


def build_providers() -> dict:
    out = {}
    for key, name, category, cls in PROVIDER_SPECS:
        out[key] = cls(key, name, category)
    return out


ADAPTERS = build_providers()


def get_provider(key: str):
    return ADAPTERS.get(key)


def catalog() -> list[dict]:
    return [p.health() for p in ADAPTERS.values()]
