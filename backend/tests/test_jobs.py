from tests.conftest import make_client
from app.db.session import SessionLocal
from app.jobs.runner import run_job
from app.models import entities as m


def test_job_runner_is_idempotent():
    make_client()

    def fn(db):
        return {"ok": True, "book_of_record_modified": False}

    db = SessionLocal()
    try:
        a = run_job(db, "daily_tlh_scan", fn, "test-tlh-1")
        b = run_job(db, "daily_tlh_scan", fn, "test-tlh-1")
        assert a.status == "success"
        assert b.id == a.id
        rows = db.query(m.JobRun).filter(m.JobRun.idempotency_key == "test-tlh-1").count()
        assert rows == 1
    finally:
        db.close()
