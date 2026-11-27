"""Chunk text and persist embeddings. Authorization is the caller's responsibility."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import entities as m
from app.ai.rag.store import hashed_embed, get_vector_store


def chunk_text(text: str, size: int = 700, overlap: int = 80) -> list[str]:
    clean = " ".join((text or "").split())
    if not clean:
        return []
    chunks = []
    i = 0
    while i < len(clean):
        chunks.append(clean[i : i + size])
        i += max(size - overlap, 1)
    return chunks


def persist_chunks(db: Session, document: m.Document, version: m.DocumentVersion, text: str) -> list[m.DocumentChunk]:
    store = get_vector_store()
    db.query(m.DocumentChunk).filter(m.DocumentChunk.document_id == document.id).delete()
    created = []
    parts = chunk_text(text) or [text[:700] or document.name]
    for idx, part in enumerate(parts):
        chunk = m.DocumentChunk(
            document_id=document.id,
            household_id=document.household_id,
            document_version_id=version.id,
            chunk_index=idx,
            text=part,
            page_number=None,
            version=1,
        )
        store.upsert(db, chunk, hashed_embed(part))
        db.add(chunk)
        created.append(chunk)
    db.flush()
    return created
