from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import DataResponse, ORMModel


class HPCConnectionConfig(BaseModel):
    hostname: str
    username: str
    port: int = 22
    ssh_key_reference: str | None = None
    key_path: str | None = None
    notes: str | None = None


class HPCConnectionRead(ORMModel):
    id: int
    hostname: str
    username: str
    port: int
    ssh_key_reference: str | None = None
    notes: str | None = None
    status: str
    is_active: bool
    created_at: datetime


class HPCSummary(BaseModel):
    status: str
    queued: int
    running: int
    gpu_free: int
    active_connection: HPCConnectionRead | None = None


class SlurmResourcesPayload(BaseModel):
    preset: str | None = None
    gpu: int = 1
    cpu: int = 16
    memory_gb: int = 64
    wall_time: str = "08:00:00"
    constraint: str | None = None
    sbatch_overrides: str | None = None


class SlurmJobSubmitRequest(BaseModel):
    job_name: str
    pipeline: str
    dataset: str
    partition: str = "gpu"
    resources: SlurmResourcesPayload
    # Optional: resolve Veritas Pipeline.yaml_definition (plugin secrets) by catalog name; else match by pipeline image.
    pipeline_name: str | None = None
    # --- MELD Graph (Atlas / IDEAS via Veritas staging) ---
    # When runtime_profile=meld_graph, pipeline should be the MELD image, e.g. meldproject/meld_graph:latest
    # Data: VERITAS_STAGED_DATASET_PATH on the compute node (from Atlas staging) or staged_dataset_path below.
    runtime_profile: str = "generic"  # generic | meld_graph
    meld_subject_id: str | None = None  # BIDS subject id, e.g. sub-01 or 01 (sub- prefix added if missing)
    meld_session: str | None = None  # BIDS session folder without "ses-" (e.g. preop, 2WK); null = no session
    staged_dataset_path: str | None = None  # Optional explicit BIDS root; else $VERITAS_STAGED_DATASET_PATH or default IDEAS path from settings


class SlurmResourcesConfig(BaseModel):
    job_name: str
    partition: str = "gpu"
    gpus: int = 1
    cpus: int = 16
    memory_gb: int = 64
    wall_time: str = "08:00:00"
    constraint: str | None = None
    sbatch_overrides: str | None = None


HPCSummaryResponse = DataResponse[HPCSummary]
HPCConnectionResponse = DataResponse[HPCConnectionRead]
HPCConnectionListResponse = DataResponse[list[HPCConnectionRead]]
