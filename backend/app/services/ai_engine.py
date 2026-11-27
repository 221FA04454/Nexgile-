from __future__ import annotations

"""Compatibility wrapper. New turns go through AIOrchestrator.

The deterministic provider remains the default when no LLM key is configured.
"""
from sqlalchemy.orm import Session

from app.models import entities as m


def chat(db: Session, user: m.User, message: str, request_id: str = "") -> dict:
    from app.ai.orchestrator import AIOrchestrator

    return AIOrchestrator(db, user, request_id=request_id).chat(message)
