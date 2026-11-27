from datetime import date
import os
import sys

os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET"] = "test-jwt-secret-not-for-production-use!"
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL") or "sqlite:///:memory:"
os.environ["ALLOW_SQLITE"] = "true"
os.environ["ALLOW_MEMORY_CACHE"] = "true"
os.environ["ALLOW_DEMO_SEED"] = "true"
os.environ["ALLOW_CREATE_ALL"] = "true"
os.environ["REDIS_URL"] = ""
os.environ["COOKIE_SECURE"] = "false"

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import get_settings
from app.core.redis import reset_redis_client

get_settings.cache_clear()

from fastapi.testclient import TestClient
from app.db.session import reset_engine, get_engine, Base, SessionLocal
from app.db.seed import seed
from app.main import app
from app import models  # noqa: F401
from app.models import entities as m


def make_client():
    reset_engine()
    reset_redis_client()
    get_settings.cache_clear()
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
        db.commit()
    finally:
        db.close()
    return TestClient(app)


def auth_header(client, email, password="demo123"):
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
