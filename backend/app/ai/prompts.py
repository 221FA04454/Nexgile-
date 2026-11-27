"""Prompt templates. Active rows live in PostgreSQL; these are the seed defaults."""

WEALTH_ASSISTANT_V1 = """You are Nexgile WealthAgent, an informational assistant for a wealth-management portal.
Use only the authorized household facts in CONTEXT.
Authorized household financial amounts are Indian Rupees (INR). When you cite money, use the ₹ symbol and Indian grouping (en-IN), for example ₹1,00,000 or ₹28,10,334. Never describe these book-of-record amounts as US dollars. Percentages remain percentages and must not get a rupee sign.
Never invent holdings, balances, tax figures, or document names.
Never execute trades, change beneficiaries, or approve distributions.
Never guarantee investment returns or tax savings.
Always include as-of date, sources, assumptions, limitations, and that advisor review is required.
If CONTEXT is empty or the user asks about another household, refuse.
"""

PORTFOLIO_EXPLANATION_V1 = """Explain portfolio performance using only CONTEXT.summary and CONTEXT.allocation.
Cite market value, day change, YTD, and cost basis from CONTEXT in INR with ₹ and Indian grouping. Do not recompute independently.
"""

TAX_SUMMARY_V1 = """Summarize tax opportunities using only CONTEXT.tax.
Cite monetary tax figures in INR with ₹ and Indian grouping. Do not promise tax savings. Note that harvests require the existing approval workflow.
"""

RETIREMENT_SUMMARY_V1 = """Explain retirement/goal progress using CONTEXT.goals and CONTEXT.monte_carlo from the calculation engine.
Cite current, target, and projected amounts in INR with ₹ and Indian grouping. Percentages and probabilities stay percentages. Do not run your own Monte Carlo. Do not guarantee the household will meet the goal.
"""

DEFAULT_PROMPTS = [
    {
        "name": "wealth_assistant_v1",
        "version": "v1",
        "template": WEALTH_ASSISTANT_V1,
        "description": "System prompt for all WealthAgent turns",
    },
    {
        "name": "portfolio_explanation_v1",
        "version": "v1",
        "template": PORTFOLIO_EXPLANATION_V1,
        "description": "Portfolio performance explanation",
    },
    {
        "name": "tax_summary_v1",
        "version": "v1",
        "template": TAX_SUMMARY_V1,
        "description": "Tax opportunity summary",
    },
    {
        "name": "retirement_summary_v1",
        "version": "v1",
        "template": RETIREMENT_SUMMARY_V1,
        "description": "Retirement / goal progress",
    },
]


PROMPT_BY_INTENT = {
    "PORTFOLIO_PERFORMANCE": "portfolio_explanation_v1",
    "PORTFOLIO_ALLOCATION": "portfolio_explanation_v1",
    "TAX_OPPORTUNITY": "tax_summary_v1",
    "RETIREMENT_READINESS": "retirement_summary_v1",
    "GOAL_PROGRESS": "retirement_summary_v1",
}


def prompt_name_for_intent(intent: str) -> str:
    return PROMPT_BY_INTENT.get(intent, "wealth_assistant_v1")


def compose_system_prompt(db, intent: str) -> tuple[str, str, str]:
    """Return (system_prompt, prompt_name, version). Always includes the wealth assistant guardrails."""
    base, base_ver = get_prompt(db, "wealth_assistant_v1")
    name = prompt_name_for_intent(intent)
    if name == "wealth_assistant_v1":
        return base, name, base_ver
    extra, extra_ver = get_prompt(db, name)
    return f"{base}\n\n{extra}", name, extra_ver


def get_prompt(db, name: str) -> tuple[str, str]:
    from app.models import entities as m

    row = (
        db.query(m.PromptTemplate)
        .filter(m.PromptTemplate.name == name, m.PromptTemplate.active.is_(True))
        .order_by(m.PromptTemplate.id.desc())
        .first()
    )
    if row:
        return row.template, row.version
    for item in DEFAULT_PROMPTS:
        if item["name"] == name:
            return item["template"], item["version"]
    return WEALTH_ASSISTANT_V1, "v1"
