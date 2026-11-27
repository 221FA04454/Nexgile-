"""Permission-aware RAG retrieval. Household filter is applied before ranking."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth.access import assigned_household_ids
from app.models import entities as m
from app.ai.rag.store import hashed_embed, get_vector_store


def retrieve_relevant_documents(db: Session, user: m.User, query: str, k: int = 5) -> list[dict]:
    allowed = assigned_household_ids(db, user)
    if not allowed:
        return []
    store = get_vector_store()
    chunks = store.search(db, allowed, hashed_embed(query), k=k)
    results = []
    for chunk in chunks:
        if chunk.household_id not in allowed:
            continue
        doc = db.query(m.Document).filter(m.Document.id == chunk.document_id).first()
        if not doc or doc.household_id not in allowed:
            continue
        results.append(
            {
                "chunk_id": chunk.id,
                "document_id": doc.id,
                "household_id": doc.household_id,
                "name": doc.name,
                "category": doc.category,
                "status": doc.status,
                "page_number": chunk.page_number,
                "text": chunk.text[:500],
            }
        )
    return results
