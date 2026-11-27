"""Central INR configuration and formatting. Numeric columns stay numeric."""
from __future__ import annotations

DEFAULT_CURRENCY = "INR"
DEFAULT_CURRENCY_SYMBOL = "₹"
DEFAULT_LOCALE = "en-IN"


def currency_meta() -> dict:
    return {
        "currency": DEFAULT_CURRENCY,
        "currency_symbol": DEFAULT_CURRENCY_SYMBOL,
        "locale": DEFAULT_LOCALE,
    }


def indian_grouped_int(n: int) -> str:
    sign = "-" if n < 0 else ""
    digits = str(abs(int(n)))
    if len(digits) <= 3:
        return f"{sign}{digits}"
    parts = [digits[-3:]]
    rest = digits[:-3]
    while rest:
        parts.append(rest[-2:])
        rest = rest[:-2]
    return f"{sign}{','.join(reversed(parts))}"


def format_inr(value, digits: int = 0) -> str:
    """Format a numeric INR amount with ₹ and Indian grouping (en-IN)."""
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if digits <= 0:
        return f"₹{indian_grouped_int(int(round(number)))}"
    rounded = round(number, digits)
    whole = int(rounded)
    frac = abs(rounded - whole)
    frac_str = f"{frac:.{digits}f}"[1:]
    prefix = "-" if rounded < 0 and whole == 0 else ""
    return f"{prefix}₹{indian_grouped_int(whole)}{frac_str}"


def with_currency(payload: dict) -> dict:
    payload.update(currency_meta())
    return payload
