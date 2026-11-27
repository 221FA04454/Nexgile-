"""Sensitive-action workflows. Previews never mutate the book of record."""

SENSITIVE = (
    "rebalance",
    "trade",
    "tax_harvest",
    "distribution",
    "beneficiary_change",
    "account_change",
)
