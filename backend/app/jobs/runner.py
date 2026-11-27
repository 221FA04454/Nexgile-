"""Job runner with retries, exponential backoff, idempotency, and dead-letter."""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy.orm import Session

from app.models import entities as m

log = logging.getLogger("wealthagent.jobs")


def run_job(
    db: Session,
    job_name: str,
    fn: Callable[[Session], dict],
    idempotency_key: str,
    max_attempts: int = 5,
) -> m.JobRun:
    existing = db.query(m.JobRun).filter(m.JobRun.idempotency_key == idempotency_key).first()
    if existing and existing.status == "success":
        log.info("job_skip_idempotent job=%s key=%s", job_name, idempotency_key)
        return existing
    if existing and existing.status == "running":
        log.info("job_skip_running job=%s key=%s", job_name, idempotency_key)
        return existing
    job = existing or m.JobRun(
        job_name=job_name,
        idempotency_key=idempotency_key,
        max_attempts=max_attempts,
        status="pending",
    )
    if (job.attempt or 0) >= (job.max_attempts or 5) and job.status == "failed":
        job.status = "dead_letter"
        db.add(job)
        db.commit()
        log.error("job_dead_letter job=%s key=%s", job_name, idempotency_key)
        return job
    job.status = "running"
    job.attempt = (job.attempt or 0) + 1
    job.started_at = datetime.now(timezone.utc)
    db.add(job)
    db.commit()
    try:
        result = fn(db)
        job.result = result
        job.status = "success"
        job.finished_at = datetime.now(timezone.utc)
        job.last_error = ""
        db.add(job)
        db.commit()
        log.info("job_success job=%s attempt=%s", job_name, job.attempt)
        return job
    except Exception as exc:
        db.rollback()
        delay = min(60, 2 ** job.attempt)
        job.status = "failed" if job.attempt < job.max_attempts else "dead_letter"
        job.last_error = type(exc).__name__
        job.finished_at = datetime.now(timezone.utc)
        db.add(job)
        db.commit()
        log.error("job_failed job=%s attempt=%s backoff=%s err=%s", job_name, job.attempt, delay, type(exc).__name__)
        if job.status != "dead_letter":
            time.sleep(delay)
        return job
