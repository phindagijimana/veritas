from __future__ import annotations

from redis import Redis
from rq import Queue
from rq.job import Retry

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.report_service import ReportService
from app.workers.job_worker import monitor_all_jobs


def _redis() -> Redis:
    return Redis.from_url(get_settings().redis_url)


def _queue() -> Queue:
    s = get_settings()
    return Queue(s.rq_queue_name, connection=_redis())


def _enqueue_opts() -> dict:
    s = get_settings()
    opts: dict = {
        "job_timeout": s.rq_job_timeout_seconds,
        "failure_ttl": s.rq_failed_job_ttl_seconds,
    }
    if s.rq_retry_max > 0:
        raw = s.rq_retry_intervals.strip()
        intervals = [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]
        if not intervals:
            intervals = [60]
        opts["retry"] = Retry(max=s.rq_retry_max, interval=intervals)
    return opts


def enqueue_report_generation(request_id: int) -> str:
    job = _queue().enqueue("app.workers.tasks.run_report_generation", request_id, **_enqueue_opts())
    return job.id


def enqueue_job_monitor_sweep() -> str:
    job = _queue().enqueue("app.workers.tasks.run_job_monitor_sweep", **_enqueue_opts())
    return job.id


def run_job_monitor_sweep() -> dict:
    return monitor_all_jobs()


def run_report_generation(request_id: int) -> dict:
    db = SessionLocal()
    try:
        report = ReportService.generate_for_request(db, request_id)
        db.commit()
        return {"request_id": request_id, "status": report.status}
    finally:
        db.close()
