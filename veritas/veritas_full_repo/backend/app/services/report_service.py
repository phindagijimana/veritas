from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.enums import ReportStatus, RequestStatus
from app.models.job import Job
from app.models.report import Report
from app.models.report_artifact import ReportArtifact
from app.schemas.report import ArtifactRead, MetricSummary, ReportCreate, ReportDetail
from app.services.artifact_storage import ArtifactStorageService
from app.services.metrics_parser import MetricsParserService
from app.services.report_generator import ReportGeneratorService
from app.services.request_service import InvalidPhaseTransitionError, RequestService


class ReportService:
    @staticmethod
    def list(db: Session) -> list[Report]:
        return list(db.scalars(select(Report).order_by(desc(Report.id))))

    @staticmethod
    def create(db: Session, payload: ReportCreate) -> Report:
        report = Report(**payload.model_dump())
        db.add(report)
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def _latest_job(db: Session, request_id: int) -> Job | None:
        return db.scalar(select(Job).where(Job.request_id == request_id).order_by(desc(Job.id)).limit(1))

    @staticmethod
    def _artifact_specs(request_code: str, job: Job | None, storage: ArtifactStorageService) -> list[dict]:
        layout = storage.job_layout(request_code, request_code)
        pdf_path = job.report_path if job and job.report_path else layout['report_path']
        json_path = job.metrics_path if job and job.metrics_path else layout['report_json_path']
        csv_path = job.results_csv_path if job and job.results_csv_path else layout['results_csv_path']
        return [
            {"kind": "PDF", "path": pdf_path, "size": "1.2 MB", "metadata": {"category": "summary"}},
            {"kind": "JSON", "path": json_path, "size": "84 KB", "metadata": {"category": "metrics"}},
            {"kind": "CSV", "path": csv_path, "size": "48 KB", "metadata": {"category": "tabular"}},
        ]

    @staticmethod
    def _ensure_artifacts(report: Report, request_code: str, job: Job | None, storage: ArtifactStorageService) -> None:
        existing = {artifact.artifact_type.upper(): artifact for artifact in report.artifacts}
        for spec in ReportService._artifact_specs(request_code, job, storage):
            artifact = existing.get(spec["kind"])
            url = storage.public_url(spec["path"])
            if artifact:
                artifact.storage_path = artifact.storage_path or spec["path"]
                artifact.download_url = artifact.download_url or url
                artifact.size_label = artifact.size_label or spec["size"]
                artifact.metadata_json = artifact.metadata_json or json.dumps(spec["metadata"])
            else:
                report.artifacts.append(
                    ReportArtifact(
                        artifact_type=spec["kind"],
                        name=spec["path"].split("/")[-1],
                        status=report.status,
                        storage_path=spec["path"],
                        download_url=url,
                        size_label=spec["size"],
                        metadata_json=json.dumps(spec["metadata"]),
                    )
                )

    @staticmethod
    def _ensure_report(db: Session, request_id: int | str) -> tuple:
        request = RequestService._resolve(db, request_id)
        if not request:
            raise ValueError("Request not found")
        report = db.scalar(select(Report).where(Report.request_id == request.id).limit(1))
        if not report:
            report = Report(request_id=request.id, status=request.report_status or ReportStatus.pending.value)
            db.add(report)
            db.flush()
        job = ReportService._latest_job(db, request.id)
        storage = ArtifactStorageService()
        bundle = ReportGeneratorService.generate_bundle(request, job, storage)
        metrics = json.loads(bundle["metrics_summary_json"])
        report.metrics_summary_json = bundle["metrics_summary_json"]
        report.pdf_path = bundle["pdf_path"]
        report.json_path = bundle["json_path"]
        report.csv_path = bundle["csv_path"]
        if job:
            job.metrics_path = bundle["metrics_path"]
            job.results_csv_path = bundle["csv_path"]
            job.report_path = bundle["pdf_path"]
            db.flush()
        ReportService._ensure_artifacts(report, request.request_code, job, storage)
        return request, report

    @staticmethod
    def publish_for_request(db: Session, request_id: int | str) -> Report:
        request = RequestService._resolve(db, request_id)
        if not request:
            raise ValueError("Request not found")
        if request.status not in {RequestStatus.reporting.value, RequestStatus.completed.value}:
            raise InvalidPhaseTransitionError("Report can only be published from the Reporting phase")
        _, report = ReportService._ensure_report(db, request.id)
        report.status = ReportStatus.ready.value
        report.published_at = datetime.utcnow()
        for artifact in report.artifacts:
            artifact.status = ReportStatus.ready.value
        if request.status == RequestStatus.reporting.value:
            RequestService.transition_request(db, request, RequestStatus.completed.value, report_status=ReportStatus.ready.value)
        else:
            request.report_status = ReportStatus.ready.value
            db.flush()
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def generate_for_request(db: Session, request_id: int | str) -> Report:
        request = RequestService._resolve(db, request_id)
        if not request:
            raise ValueError("Request not found")
        if request.status not in {RequestStatus.processing.value, RequestStatus.reporting.value, RequestStatus.completed.value}:
            raise InvalidPhaseTransitionError("Report generation can only start after Processing")
        if request.status == RequestStatus.processing.value:
            RequestService.transition_request(db, request, RequestStatus.reporting.value, report_status=ReportStatus.preparing.value)
        else:
            request.report_status = ReportStatus.preparing.value
            db.flush()
        _, report = ReportService._ensure_report(db, request.id)
        report.status = ReportStatus.preparing.value
        for artifact in report.artifacts:
            artifact.status = ReportStatus.preparing.value
        db.commit()
        db.refresh(report)
        return report

    @staticmethod
    def detail_for_request(db: Session, request_id: int | str) -> ReportDetail:
        request = RequestService._resolve(db, request_id)
        if not request:
            raise ValueError("Request not found")
        _, report = ReportService._ensure_report(db, request.id)
        db.commit()
        metrics = MetricSummary(**json.loads(report.metrics_summary_json)) if report.metrics_summary_json else None
        artifacts: list[ArtifactRead] = []
        for artifact in report.artifacts:
            metadata = json.loads(artifact.metadata_json) if artifact.metadata_json else None
            artifacts.append(
                ArtifactRead(
                    id=f"{request.request_code}-{artifact.artifact_type.lower()}",
                    name=artifact.name,
                    type=artifact.artifact_type,
                    status=artifact.status.title(),
                    url=artifact.download_url,
                    size=artifact.size_label,
                    metadata=metadata,
                )
            )
        return ReportDetail(
            request_id=request.request_code,
            status=report.status.title(),
            generated_at=report.created_at,
            published_at=report.published_at,
            metrics_summary=metrics,
            artifacts=artifacts,
        )

    @staticmethod
    def download_link(db: Session, request_id: int | str, fmt: str) -> str:
        request = RequestService._resolve(db, request_id)
        if not request:
            raise ValueError("Request not found")
        _, report = ReportService._ensure_report(db, request.id)
        for artifact in report.artifacts:
            if artifact.artifact_type.lower() == fmt.lower():
                return artifact.download_url or artifact.storage_path or ""
        raise ValueError(f"{fmt.upper()} artifact not found")
