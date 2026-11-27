"""AI RAG tables: prompts, document versions/chunks, interaction log.

Revision ID: 002_ai_rag
Revises: 001_initial
Create Date: 2026-09-07
"""
from alembic import op

from app import models  # noqa: F401
from app.models.entities import PromptTemplate, DocumentVersion, DocumentChunk, AIInteraction

revision = "002_ai_rag"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    PromptTemplate.__table__.create(bind=bind, checkfirst=True)
    DocumentVersion.__table__.create(bind=bind, checkfirst=True)
    DocumentChunk.__table__.create(bind=bind, checkfirst=True)
    AIInteraction.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    AIInteraction.__table__.drop(bind=bind, checkfirst=True)
    DocumentChunk.__table__.drop(bind=bind, checkfirst=True)
    DocumentVersion.__table__.drop(bind=bind, checkfirst=True)
    PromptTemplate.__table__.drop(bind=bind, checkfirst=True)
