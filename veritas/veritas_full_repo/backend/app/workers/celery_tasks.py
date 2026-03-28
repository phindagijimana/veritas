"""Celery task implementations (formerly RQ)."""

from __future__ import annotations

from app.celery_app import celery_app
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.services.report_service import ReportService
from app.workers.job_worker import monitor_all_jobs

_max_retries = get_settings().rq_retry_max


@celery_app.task(
    name="veritas.run_job_monitor_sweep",
    bind=True,
    max_retries=_max_retries,
)
def run_job_monitor_sweep_task(self) -> dict:
    try:
        return monitor_all_jobs()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60) from exc


@celery_app.task(
    name="veritas.run_report_generation",
    bind=True,
    max_retries=_max_retries,
)
def run_report_generation_task(self, request_id: int) -> dict:
    db = SessionLocal()
    try:
        report = ReportService.generate_for_request(db, request_id)
        db.commit()
        return {"request_id": request_id, "status": report.status}
    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        db.close()
