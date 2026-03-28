
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import JobStatus, ReportStatus, RequestStatus
from app.models.job import Job
from app.models.report import Report
from app.services.hpc_adapter import get_hpc_adapter
from app.services.hpc_service import HPCConnectionService
from app.services.request_service import RequestService


SCHEDULER_TO_JOB_STATUS = {
    "PENDING": JobStatus.queued.value,
    "CONFIGURING": JobStatus.queued.value,
    "RUNNING": JobStatus.running.value,
    "COMPLETED": JobStatus.completed.value,
    "COMPLETING": JobStatus.running.value,
    "FAILED": JobStatus.failed.value,
    "TIMEOUT": JobStatus.failed.value,
    "OUT_OF_MEMORY": JobStatus.failed.value,
    "CANCELLED": JobStatus.cancelled.value,
    "CANCELLED+": JobStatus.cancelled.value,
    "PREEMPTED": JobStatus.failed.value,
    "NODE_FAIL": JobStatus.failed.value,
    "BOOT_FAIL": JobStatus.failed.value,
    "QUEUED": JobStatus.queued.value,
}


class JobMonitorService:
    @staticmethod
    def sync_job(db: Session, job: Job) -> Job:
        connection = HPCConnectionService.get_active_connection(db)
        if not connection or not job.scheduler_job_id:
            return job
        adapter = get_hpc_adapter()
        scheduler_state = adapter.status(connection, job.scheduler_job_id)
        mapped_status = SCHEDULER_TO_JOB_STATUS.get(scheduler_state.upper(), job.status)
        if mapped_status != job.status:
            JobMonitorService._apply_status(db, job, mapped_status)
        job.last_scheduler_sync_at = datetime.utcnow()
        db.flush()
        return job

    @staticmethod
    def cancel_job(db: Session, job: Job) -> Job:
        connection = HPCConnectionService.get_active_connection(db)
        if connection and job.scheduler_job_id:
            adapter = get_hpc_adapter()
            adapter.cancel(connection, job.scheduler_job_id)
        JobMonitorService._apply_status(db, job, JobStatus.cancelled.value)
        job.last_scheduler_sync_at = datetime.utcnow()
        db.flush()
        return job

    @staticmethod
    def _apply_status(db: Session, job: Job, status: str) -> None:
        job.status = status
        request = job.request
        if not request:
            return
        if status == JobStatus.running.value and request.status == RequestStatus.data_prep.value:
            RequestService.transition_request(
                db,
                request,
                RequestStatus.processing.value,
                report_status=ReportStatus.preparing.value,
            )
        elif status == JobStatus.completed.value:
            if request.status == RequestStatus.processing.value:
                RequestService.transition_request(
                    db,
                    request,
                    RequestStatus.reporting.value,
                    report_status=ReportStatus.ready.value,
                )
            report = db.scalar(select(Report).where(Report.request_id == request.id).limit(1))
            if report:
                report.status = ReportStatus.ready.value
        elif status in {JobStatus.failed.value, JobStatus.cancelled.value}:
            request.status = RequestStatus.failed.value
            request.report_status = ReportStatus.pending.value
