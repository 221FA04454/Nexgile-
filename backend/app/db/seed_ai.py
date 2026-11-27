"""AI prompt templates and document chunks for an existing book of record."""
from sqlalchemy.orm import Session

from app.ai.prompts import DEFAULT_PROMPTS
from app.ai.rag.ingest import ingest_household_documents
from app.models import entities as m


def seed_ai_layer(db: Session) -> None:
    if not db.query(m.PromptTemplate).first():
        for item in DEFAULT_PROMPTS:
            db.add(
                m.PromptTemplate(
                    name=item["name"],
                    version=item["version"],
                    template=item["template"],
                    description=item["description"],
                    active=True,
                )
            )
        db.flush()
    ingest_household_documents(db)
