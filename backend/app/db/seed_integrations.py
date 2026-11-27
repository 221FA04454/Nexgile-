from sqlalchemy.orm import Session

from app.integrations.registry import PROVIDER_SPECS
from app.models import entities as m


def seed_integrations(db: Session) -> None:
    existing = {c.provider_key for c in db.query(m.IntegrationConnection).all()}
    for key, name, category, _cls in PROVIDER_SPECS:
        if key in existing:
            continue
        db.add(
            m.IntegrationConnection(
                provider_key=key,
                display_name=name,
                category=category,
                status="mock",
                live=False,
                freshness="unknown",
            )
        )
    db.flush()
