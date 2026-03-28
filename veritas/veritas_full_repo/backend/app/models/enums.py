from __future__ import annotations

from enum import Enum


class RequestStatus(str, Enum):
    submitted = "submitted"
    pipeline_prep = "pipeline_prep"
    data_prep = "data_prep"
    processing = "processing"
    reporting = "reporting"
    completed = "completed"
    failed = "failed"


class JobStatus(str, Enum):
    created = "created"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ReportStatus(str, Enum):
    pending = "pending"
    preparing = "preparing"
    ready = "ready"


class DatasetModality(str, Enum):
    mri = "MRI"
    eeg = "EEG"
    ct = "CT"
    multimodal = "Multimodal"
