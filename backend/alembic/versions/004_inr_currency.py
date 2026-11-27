"""Account currency default INR.

Revision ID: 004_inr_currency
Revises: 003_integrations
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa

revision = "004_inr_currency"
down_revision = "003_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE accounts SET currency = 'INR' WHERE currency IS NULL OR currency = 'USD'"))


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE accounts SET currency = 'USD' WHERE currency = 'INR'"))
