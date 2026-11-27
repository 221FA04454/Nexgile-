"""Vector store abstraction. JSON embeddings in PostgreSQL/SQLite.

pgvector is not bundled in postgres:16-alpine. Production can swap PgVectorStore
when the extension is available without changing callers.
"""
from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import entities as m

TOKEN = re.compile(r"[a-z0-9$%]+")


def tokenize(text: str) -> list[str]:
    return TOKEN.findall((text or "").lower())


def hashed_embed(text: str, dim: int | None = None) -> list[float]:
    dim = dim or get_settings().embedding_dim
    vec = [0.0] * dim
    for tok in tokenize(text):
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:2], "big") % dim
        sign = 1.0 if digest[2] % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 6) for x in vec]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(a[i] * a[i] for i in range(n))) or 1.0
    nb = math.sqrt(sum(b[i] * b[i] for i in range(n))) or 1.0
    return dot / (na * nb)


class VectorStore(Protocol):
    def upsert(self, db: Session, chunk: m.DocumentChunk, vector: list[float]) -> None: ...
    def search(self, db: Session, household_ids: set[int], query_vector: list[float], k: int = 6) -> list[m.DocumentChunk]: ...
    def backend_name(self) -> str: ...


class JsonVectorStore:
    """Development/default store: embeddings in JSON, cosine in process.

    Authorization filter is applied in SQL before ranking.
    """

    def backend_name(self) -> str:
        return "json_cosine"

    def upsert(self, db: Session, chunk: m.DocumentChunk, vector: list[float]) -> None:
        chunk.embedding = vector
        db.add(chunk)

    def search(self, db: Session, household_ids: set[int], query_vector: list[float], k: int = 6) -> list[m.DocumentChunk]:
        if not household_ids:
            return []
        rows = (
            db.query(m.DocumentChunk)
            .filter(m.DocumentChunk.household_id.in_(household_ids))
            .all()
        )
        scored = [(cosine(query_vector, row.embedding or []), row) for row in rows]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [row for score, row in scored[:k] if score > 0.02]


class PgVectorStore:
    """Production interface. Requires CREATE EXTENSION vector — not enabled in the current image."""

    def backend_name(self) -> str:
        return "pgvector_unavailable"

    def upsert(self, db: Session, chunk: m.DocumentChunk, vector: list[float]) -> None:
        JsonVectorStore().upsert(db, chunk, vector)

    def search(self, db: Session, household_ids: set[int], query_vector: list[float], k: int = 6):
        return JsonVectorStore().search(db, household_ids, query_vector, k)


def get_vector_store() -> VectorStore:
    return JsonVectorStore()
