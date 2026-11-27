"""Document ingestion: validate → extract → chunk → embed → store."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.documents.storage import get_storage
from app.models import entities as m
from app.ai.rag.extract import extract_text
from app.ai.rag.chunk import persist_chunks


def metadata_corpus(doc: m.Document) -> str:
    return " ".join(
        [
            doc.name or "",
            doc.category or "",
            doc.doc_type or "",
            doc.status or "",
            doc.owner or "",
            doc.ai_classification or "",
            f"review {doc.expiry_or_review}" if doc.expiry_or_review else "",
        ]
    )


def ingest_document(db: Session, document: m.Document, raw: bytes | None = None, content_type: str = "") -> m.DocumentVersion:
    text = ""
    extractor = "metadata"
    if raw:
        text, extractor = extract_text(raw, content_type, document.name or "")
    elif document.file_path:
        try:
            raw = get_storage().get(document.file_path)
            text, extractor = extract_text(raw, content_type, document.name or "")
        except Exception:
            text, extractor = "", "storage_miss"
    if not (text or "").strip():
        text = metadata_corpus(document)
        extractor = "metadata"
    version = m.DocumentVersion(
        document_id=document.id,
        household_id=document.household_id,
        version=document.version or "1.0",
        storage_key=document.file_path or "",
        extracted_text=text[:20000],
        extractor=extractor,
    )
    db.add(version)
    db.flush()
    persist_chunks(db, document, version, text)
    return version


def ingest_household_documents(db: Session) -> int:
    count = 0
    docs = db.query(m.Document).all()
    existing = {c.document_id for c in db.query(m.DocumentChunk.document_id).distinct()}
    for doc in docs:
        if doc.id in existing:
            continue
        ingest_document(db, doc)
        count += 1
    return count
