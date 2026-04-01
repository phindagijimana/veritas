from __future__ import annotations

import re

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.enums import JobStatus, ReportStatus, RequestStatus
from app.models.pipeline import Pipeline
from app.models.request import EvaluationRequest
from app.schemas.request import EvaluationRequestCreate, EvaluationRequestRead, EvaluationRequestStatusUpdate, TimelineItem

PHASE_ORDER = [
    (RequestStatus.submitted.value, "Submitted"),
    (RequestStatus.pipeline_prep.value, "Pipeline Prep"),
    (RequestStatus.data_prep.value, "Data Prep"),
    (RequestStatus.processing.value, "Processing"),
    (RequestStatus.reporting.value, "Reporting"),
    (RequestStatus.completed.value, "Completed"),
    (RequestStatus.failed.value, "Failed"),
]
PHASE_LABEL_TO_CODE = {label: code for code, label in PHASE_ORDER}
PHASE_CODE_TO_LABEL = {code: label for code, label in PHASE_ORDER}
TRANSITION_RULES = {
    RequestStatus.submitted.value: {RequestStatus.pipeline_prep.value, RequestStatus.failed.value},
    RequestStatus.pipeline_prep.value: {RequestStatus.data_prep.value, RequestStatus.failed.value},
    RequestStatus.data_prep.value: {RequestStatus.processing.value, RequestStatus.failed.value},
    RequestStatus.processing.value: {RequestStatus.reporting.value, RequestStatus.failed.value},
    RequestStatus.reporting.value: {RequestStatus.completed.value, RequestStatus.failed.value},
    RequestStatus.completed.value: set(),
    RequestStatus.failed.value: set(),
}


class InvalidPhaseTransitionError(ValueError):
    pass


class RequestService:
    @staticmethod
    def _to_read(item: EvaluationRequest) -> EvaluationRequestRead:
        current_index = next((i for i, (code, _) in enumerate(PHASE_ORDER) if code == item.status), 0)
        timeline = [
            TimelineItem(code=code, label=label, active=i == current_index, complete=i < current_index)
            for i, (code, label) in enumerate(PHASE_ORDER)
            if code != RequestStatus.failed.value
        ]
        datasets = [item.dataset.name] if item.dataset else []
        return EvaluationRequestRead(
            id=item.request_code,
            request_id=item.id,
            datasets=datasets,
            submitted_at=item.created_at,
            current_phase=PHASE_CODE_TO_LABEL.get(item.status, item.status.title()),
            report_status=item.report_status.replace("_", " ").title(),
            admin_note=item.admin_note,
            timeline=timeline,
            pipeline=item.pipeline.image if item.pipeline else None,
            pipeline_id=item.pipeline_id,
            dataset_ids=[item.dataset_id],
            description=item.description,
        )

    @staticmethod
    def list(db: Session) -> list[EvaluationRequestRead]:
        items = list(db.scalars(select(EvaluationRequest).order_by(desc(EvaluationRequest.id))))
        return [RequestService._to_read(item) for item in items]

    @staticmethod
    def create(db: Session, payload: EvaluationRequestCreate) -> EvaluationRequestRead:
        pipeline = db.scalar(select(Pipeline).where(Pipeline.image == payload.pipeline).limit(1))
        if not pipeline:
            pipeline = db.scalar(select(Pipeline).where(Pipeline.name == payload.pipeline).limit(1))
        if not pipeline:
            pipeline = Pipeline(
                name=payload.pipeline.split(":")[0].split("/")[-1].replace("_", "-"),
                title=payload.pipeline.split("/")[-1],
                image=payload.pipeline,
                modality="MRI",
                yaml_definition="name: auto-generated\n",
            )
            db.add(pipeline)
            db.flush()

        dataset_name = payload.datasets[0] if payload.datasets else "Default Dataset"
        dataset = db.scalar(select(Dataset).where(Dataset.name == dataset_name).limit(1))
        if not dataset:
            base = re.sub(r"[^A-Za-z0-9]+", "-", dataset_name.strip()).strip("-").upper()[:24] or "DATASET"
            code = base[:32]
            n = 0
            while db.scalar(select(Dataset).where(Dataset.code == code).limit(1)):
                n += 1
                suffix = f"-{n}"
                code = f"{base[: 32 - len(suffix)]}{suffix}"[:32]
            dataset = Dataset(
                code=code,
                name=dataset_name,
                disease_group="General",
                modality="MRI",
            )
            db.add(dataset)
            db.flush()

        next_id = db.scalar(select(EvaluationRequest.id).order_by(desc(EvaluationRequest.id)).limit(1)) or 1037
        request_code = f"REQ-{next_id + 1}"
        item = EvaluationRequest(
            request_code=request_code,
            description=payload.description,
            pipeline_id=pipeline.id,
            dataset_id=dataset.id,
            status=RequestStatus.submitted.value,
            report_status=ReportStatus.pending.value,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return RequestService._to_read(item)

    @staticmethod
    def normalize_phase(phase: str) -> str:
        return PHASE_LABEL_TO_CODE.get(phase, str(phase).strip().lower().replace(" ", "_"))

    @staticmethod
    def can_transition(current_status: str, next_status: str) -> bool:
        if current_status == next_status:
            return True
        return next_status in TRANSITION_RULES.get(current_status, set())

    @staticmethod
    def enforce_transition(item: EvaluationRequest, next_status: str) -> None:
        if not RequestService.can_transition(item.status, next_status):
            current_label = PHASE_CODE_TO_LABEL.get(item.status, item.status)
            next_label = PHASE_CODE_TO_LABEL.get(next_status, next_status)
            raise InvalidPhaseTransitionError(
                f"Invalid request phase transition: {current_label} -> {next_label}"
            )

    @staticmethod
    def transition_request(db: Session, request: EvaluationRequest, next_status: str, *, report_status: str | None = None, admin_note: str | None = None) -> EvaluationRequest:
        normalized = RequestService.normalize_phase(next_status)
        RequestService.enforce_transition(request, normalized)
        request.status = normalized
        if report_status is not None:
            request.report_status = report_status
        if admin_note is not None:
            request.admin_note = admin_note
        db.flush()
        return request

    @staticmethod
    def update_status(db: Session, request_id: int | str, payload: EvaluationRequestStatusUpdate) -> EvaluationRequestRead | None:
        item = RequestService._resolve(db, request_id)
        if not item:
            return None
        next_status = RequestService.normalize_phase(payload.current_phase)
        RequestService.transition_request(db, item, next_status, admin_note=payload.admin_note)
        db.commit()
        db.refresh(item)
        return RequestService._to_read(item)

    @staticmethod
    def detail(db: Session, request_id: int | str) -> EvaluationRequestRead | None:
        item = RequestService._resolve(db, request_id)
        if not item:
            return None
        return RequestService._to_read(item)

    @staticmethod
    def _resolve(db: Session, request_id: int | str) -> EvaluationRequest | None:
        if isinstance(request_id, int) or str(request_id).isdigit():
            return db.get(EvaluationRequest, int(request_id))
        return db.scalar(select(EvaluationRequest).where(EvaluationRequest.request_code == str(request_id)).limit(1))
