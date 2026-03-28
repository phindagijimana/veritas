
from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.enums import JobStatus, ReportStatus
from app.models.job import Job
from app.services.job_monitor import JobMonitorService
from app.services.report_service import ReportService


def monitor_all_jobs() -> dict:
    db: Session = SessionLocal()
    try:
        jobs = list(db.scalars(select(Job).where(Job.status.in_([JobStatus.queued.value, JobStatus.running.value]))))
        processed = []
        for job in jobs:
            previous_status = job.status
            updated = JobMonitorService.sync_job(db, job)
            processed.append({'job_id': updated.id, 'previous_status': previous_status, 'status': updated.status})
            if updated.status == JobStatus.completed.value:
                report = ReportService.generate_for_request(db, updated.request_id)
                if report.status == ReportStatus.preparing.value:
                    ReportService.publish_for_request(db, updated.request_id)
            elif updated.status in {JobStatus.failed.value, JobStatus.cancelled.value}:
                # preserve failure state and allow operator follow-up
                pass
        db.commit()
        return {'processed': processed, 'count': len(processed), 'swept_at': datetime.utcnow().isoformat()}
    finally:
        db.close()


def monitor_loop(poll_interval_seconds: int = 30, max_iterations: int | None = None) -> None:
    import time
    iterations = 0
    while True:
        monitor_all_jobs()
        iterations += 1
        if max_iterations is not None and iterations >= max_iterations:
            return
        time.sleep(max(1, poll_interval_seconds))
