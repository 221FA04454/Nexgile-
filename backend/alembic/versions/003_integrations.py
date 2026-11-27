"""Integration metadata tables.

Revision ID: 003_integrations
Revises: 002_ai_rag
Create Date: 2026-09-07
"""
from alembic import op

from app import models  # noqa: F401
from app.models.entities import (
    IntegrationConnection,
    IntegrationRecordLink,
    IntegrationSyncRun,
    ReconciliationException,
)

revision = "003_integrations"
down_revision = "002_ai_rag"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    IntegrationConnection.__table__.create(bind=bind, checkfirst=True)
    IntegrationSyncRun.__table__.create(bind=bind, checkfirst=True)
    IntegrationRecordLink.__table__.create(bind=bind, checkfirst=True)
    ReconciliationException.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    ReconciliationException.__table__.drop(bind=bind, checkfirst=True)
    IntegrationRecordLink.__table__.drop(bind=bind, checkfirst=True)
    IntegrationSyncRun.__table__.drop(bind=bind, checkfirst=True)
    IntegrationConnection.__table__.drop(bind=bind, checkfirst=True)
