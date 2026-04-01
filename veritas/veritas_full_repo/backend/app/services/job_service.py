from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.enums import JobStatus, ReportStatus, RequestStatus
from app.models.job import Job
from app.models.pipeline import Pipeline
from app.models.report import Report
from app.models.request import EvaluationRequest
from app.schemas.hpc import SlurmJobSubmitRequest


def _meld_subjects_present(payload: SlurmJobSubmitRequest) -> bool:
    ids = [str(x).strip() for x in (payload.meld_subject_ids or []) if x is not None and str(x).strip()]
    if ids:
        return True
    return bool((payload.meld_subject_id or "").strip())
from app.core.config import get_settings
from app.schemas.job import JobAdvanceResult, JobPreviewRead, JobRead
from app.services.hpc_service import HPCConnectionService
from app.services.hpc_scheduler import HPCSchedulerService
from app.services.job_monitor import JobMonitorService
from app.services.request_service import InvalidPhaseTransitionError, RequestService

ADVANCE_SEQUENCE = {
    JobStatus.queued.value: JobStatus.running.value,
    JobStatus.running.value: JobStatus.completed.value,
    JobStatus.completed.value: JobStatus.completed.value,
    JobStatus.failed.value: JobStatus.failed.value,
    JobStatus.cancelled.value: JobStatus.cancelled.value,
    JobStatus.created.value: JobStatus.queued.value,
}


class JobService:
    @staticmethod
    def _to_read(job: Job, *, include_script: bool = False) -> JobRead:
        request_code = job.request.request_code if job.request else str(job.request_id)
        return JobRead(
            id=job.scheduler_job_id or f"JOB-{job.id}",
            job_id=job.id,
            request_id=request_code,
            scheduler_job_id=job.scheduler_job_id,
            status=job.status.title(),
            partition=job.partition,
            resources=job.resources,
            updated_at=job.last_scheduler_sync_at or job.created_at,
            pipeline_ref=job.pipeline_ref,
            dataset_name=job.dataset_name,
            runtime_engine=job.runtime_engine,
            remote_workdir=job.remote_workdir,
            stdout_path=job.stdout_path,
            stderr_path=job.stderr_path,
            runtime_manifest_path=job.runtime_manifest_path,
            metrics_path=job.metrics_path,
            results_csv_path=job.results_csv_path,
            report_path=job.report_path,
            sbatch_script=(job.sbatch_script if include_script else None),
        )

    @staticmethod
    def list(db: Session) -> list[JobRead]:
        items = list(db.scalars(select(Job).order_by(desc(Job.id))))
        return [JobService._to_read(job) for job in items]

    @staticmethod
    def summary(db: Session) -> dict[str, int]:
        queued = db.scalar(select(func.count()).select_from(Job).where(Job.status == JobStatus.queued.value)) or 0
        running = db.scalar(select(func.count()).select_from(Job).where(Job.status == JobStatus.running.value)) or 0
        return {"queued": int(queued), "running": int(running)}

    @staticmethod
    def get(db: Session, job_id: int, sync: bool = True, *, include_script: bool = False) -> JobRead | None:
        item = db.get(Job, job_id)
        if not item:
            return None
        if sync:
            JobMonitorService.sync_job(db, item)
            db.commit()
            db.refresh(item)
        return JobService._to_read(item, include_script=include_script)

    @staticmethod
    def submit_slurm_job(db: Session, request_id: int | str, payload: SlurmJobSubmitRequest) -> JobRead:
        request = RequestService._resolve(db, request_id)
        if not request:
            raise ValueError("Request not found")
        if request.status == RequestStatus.completed.value:
            raise InvalidPhaseTransitionError("Cannot submit a job for a completed request")
        if request.status == RequestStatus.submitted.value:
            RequestService.transition_request(db, request, RequestStatus.pipeline_prep.value)
        if request.status == RequestStatus.pipeline_prep.value:
            RequestService.transition_request(db, request, RequestStatus.data_prep.value)
        if request.status == RequestStatus.data_prep.value:
            RequestService.transition_request(db, request, RequestStatus.processing.value, report_status=ReportStatus.preparing.value)
        elif request.status == RequestStatus.processing.value:
            request.report_status = ReportStatus.preparing.value
            db.flush()

        rp = (payload.runtime_profile or "generic").strip().lower()
        if rp == "meld_graph" and not _meld_subjects_present(payload):
            raise ValueError(
                "meld_subject_id or meld_subject_ids is required when runtime_profile=meld_graph"
            )

        pipeline_yaml: str | None = None
        name_ref = (payload.pipeline_name or "").strip()
        if name_ref:
            row = db.query(Pipeline).filter(Pipeline.name == name_ref).first()
            if row:
                pipeline_yaml = row.yaml_definition
        if pipeline_yaml is None:
            row = db.query(Pipeline).filter(Pipeline.image == payload.pipeline).first()
            if row:
                pipeline_yaml = row.yaml_definition

        scheduler = HPCSchedulerService()
        connection = HPCConnectionService.get_active_connection(db)
        result = scheduler.submit(connection, request.request_code, payload, pipeline_yaml=pipeline_yaml)
        if not result.scheduler_job_id:
            msg = (result.submit_error or "").strip() or "Slurm sbatch did not return a job id."
            raise ValueError(msg)

        resources = f"{payload.resources.gpu} GPU • {payload.resources.cpu} CPU • {payload.resources.memory_gb} GB RAM"
        job = Job(
            request_id=request.id,
            job_name=payload.job_name,
            scheduler_job_id=result.scheduler_job_id,
            status=result.status,
            partition=payload.partition,
            resources=resources,
            pipeline_ref=payload.pipeline,
            dataset_name=payload.dataset,
            runtime_engine=result.runtime_engine,
            sbatch_script=result.sbatch_script,
            remote_workdir=result.remote_workdir,
            stdout_path=result.stdout_path,
            stderr_path=result.stderr_path,
            runtime_manifest_path=result.runtime_manifest_path,
            metrics_path=result.metrics_path,
            results_csv_path=result.results_csv_path,
            report_path=result.report_path,
            last_scheduler_sync_at=datetime.utcnow(),
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return JobService._to_read(job)

    @staticmethod
    def preview_slurm_job(db: Session, request_id: int | str, payload: SlurmJobSubmitRequest) -> JobPreviewRead:
        """Build Slurm + MELD/runtime scripts without persisting a job or calling SSH/sbatch."""
        request = RequestService._resolve(db, request_id)
        if not request:
            raise ValueError("Request not found")
        if request.status == RequestStatus.completed.value:
            raise ValueError("Cannot preview for a completed request")

        rp = (payload.runtime_profile or "generic").strip().lower()
        if rp == "meld_graph" and not _meld_subjects_present(payload):
            raise ValueError(
                "meld_subject_id or meld_subject_ids is required when runtime_profile=meld_graph"
            )

        pipeline_yaml: str | None = None
        name_ref = (payload.pipeline_name or "").strip()
        if name_ref:
            row = db.query(Pipeline).filter(Pipeline.name == name_ref).first()
            if row:
                pipeline_yaml = row.yaml_definition
        if pipeline_yaml is None:
            row = db.query(Pipeline).filter(Pipeline.image == payload.pipeline).first()
            if row:
                pipeline_yaml = row.yaml_definition

        scheduler = HPCSchedulerService()
        bundle = scheduler.preview(request.request_code, payload, pipeline_yaml=pipeline_yaml)
        settings = get_settings()
        return JobPreviewRead(
            runtime_engine=bundle.runtime_engine,
            hpc_mode=settings.hpc_mode,
            meld_ideas_default_staging_path=settings.meld_ideas_default_staging_path,
            hpc_job_prologue_sh=(settings.hpc_job_prologue_sh or "").strip() or None,
            sbatch_script=bundle.sbatch_script,
            pipeline_runtime_script=bundle.pipeline_runtime_script,
            remote_workdir=bundle.remote_workdir,
            stdout_path=bundle.stdout_path,
            stderr_path=bundle.stderr_path,
            runtime_manifest_path=bundle.runtime_manifest_path,
            launch_command=bundle.launch_command,
            metrics_path=bundle.metrics_path,
            results_csv_path=bundle.results_csv_path,
            report_path=bundle.report_path,
        )

    @staticmethod
    def sync(db: Session, job_id: int) -> JobRead | None:
        job = db.get(Job, job_id)
        if not job:
            return None
        JobMonitorService.sync_job(db, job)
        db.commit()
        db.refresh(job)
        return JobService._to_read(job)

    @staticmethod
    def cancel(db: Session, job_id: int) -> JobRead | None:
        job = db.get(Job, job_id)
        if not job:
            return None
        JobMonitorService.cancel_job(db, job)
        db.commit()
        db.refresh(job)
        return JobService._to_read(job)

    @staticmethod
    def advance(db: Session, job_id: int) -> JobAdvanceResult | None:
        job = db.get(Job, job_id)
        if not job:
            return None
        request = db.get(EvaluationRequest, job.request_id)
        if not request:
            return None

        job.status = ADVANCE_SEQUENCE.get(job.status, job.status)
        if job.status == JobStatus.running.value:
            if request.status == RequestStatus.data_prep.value:
                RequestService.transition_request(db, request, RequestStatus.processing.value, report_status=ReportStatus.preparing.value)
            elif request.status == RequestStatus.processing.value:
                request.report_status = ReportStatus.preparing.value
                db.flush()
        elif job.status == JobStatus.completed.value:
            if request.status == RequestStatus.processing.value:
                RequestService.transition_request(db, request, RequestStatus.reporting.value, report_status=ReportStatus.ready.value)
            report = db.scalar(select(Report).where(Report.request_id == request.id).limit(1))
            if not report:
                report = Report(
                    request_id=request.id,
                    status=ReportStatus.ready.value,
                    pdf_path=job.report_path,
                    json_path=job.metrics_path,
                    csv_path=job.results_csv_path,
                )
                db.add(report)
            else:
                report.status = ReportStatus.ready.value
                report.pdf_path = report.pdf_path or job.report_path
                report.json_path = report.json_path or job.metrics_path
                report.csv_path = report.csv_path or job.results_csv_path
        elif job.status in {JobStatus.failed.value, JobStatus.cancelled.value}:
            request.status = RequestStatus.failed.value
            request.report_status = ReportStatus.pending.value
            db.flush()
        db.commit()
        db.refresh(job)
        db.refresh(request)
        return JobAdvanceResult(job=JobService._to_read(job), request_status=request.status, report_status=request.report_status)
