"""Auth lifecycle columns and one-time token table.

Revision ID: 005_auth_lifecycle
Revises: 004_inr_currency
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa

revision = "005_auth_lifecycle"
down_revision = "004_inr_currency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(length=128), server_default="", nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=128), server_default="", nullable=True))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(), nullable=True))
    op.add_column("users", sa.Column("mfa_enabled", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("otp_hash", sa.String(length=128), server_default=""),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("request_id", sa.String(length=64), server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"])
    op.create_index("ix_auth_tokens_purpose", "auth_tokens", ["purpose"])
    op.create_index("ix_auth_tokens_expires_at", "auth_tokens", ["expires_at"])
    op.create_index("ix_auth_tokens_user_purpose", "auth_tokens", ["user_id", "purpose"])
    op.create_unique_constraint("uq_auth_tokens_token_hash", "auth_tokens", ["token_hash"])


def downgrade() -> None:
    op.drop_table("auth_tokens")
    op.drop_column("users", "mfa_enabled")
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "email_verified_at")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
