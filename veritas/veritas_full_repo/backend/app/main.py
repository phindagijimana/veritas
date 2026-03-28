from __future__ import annotations

from contextlib import asynccontextmanager

import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.router import api_router
from app.api.routes.health import readiness as readiness_probe
from app.core.config import get_settings, trusted_hosts_list, validate_production_settings
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.auth_rate_limit import AuthRateLimitMiddleware
from app.core.rate_limit import limiter
from app.core.request_limits import LimitRequestBodySizeMiddleware
from app.core.telemetry import REQUEST_COUNT, REQUEST_LATENCY
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Dataset, EvaluationRequest, HPCConnection, Job, Pipeline, Report, ReportArtifact

settings = get_settings()

# Synced to DB on every startup via _ensure_meld_and_ideas_catalog (existing rows get updated).
_MELD_GRAPH_FCD_YAML = """name: meld-graph-fcd
title: MELD Graph FCD (T1w)
image: docker.io/meldproject/meld_graph:latest
modality: MRI
entrypoint: python scripts/new_patient_pipeline/new_pt_pipeline.py
inputs:
  - name: bids_t1
    type: BIDS
outputs:
  - name: predictions
    type: directory
resources:
  cpu: 16
runtime_profile: meld_graph
atlas_dataset_id: ideas
plugin:
  type: meld_graph
  # Separate FreeSurfer vs MELD images (Slurm script runs the MELD image; FS image is declared for recon / ops).
  containers:
    freesurfer: docker.io/freesurfer/freesurfer:7.4.1
    meld: docker.io/meldproject/meld_graph:latest
  secrets:
    freesurfer_license_file: license.txt
    meld_license_file: meld_license.txt
  container_env:
    FS_LICENSE: /run/secrets/license.txt
    MELD_LICENSE: /run/secrets/meld_license.txt
"""
_MELD_GRAPH_FCD_TITLE = "MELD Graph — FCD lesion (T1w)"
_MELD_GRAPH_FCD_IMAGE = "docker.io/meldproject/meld_graph:latest"
_MELD_GRAPH_FCD_DESCRIPTION = (
    "MELD Project FCD classifier. Use with Atlas dataset `ideas`. "
    "Slurm submit: runtime_profile=meld_graph, meld_subject_id=sub-..., dataset ideas. "
    "YAML includes plugin.type meld_graph (FreeSurfer + MELD license files)."
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        method = request.method
        path = request.url.path
        REQUEST_COUNT.labels(method=method, path=path, status=str(response.status_code)).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
        return response



def seed_data() -> None:
    db = SessionLocal()
    try:
        if not db.query(Dataset).first():
            db.add_all(
                [
                    Dataset(code="HS", name="HS Dataset", disease_group="Hippocampal Sclerosis", collection_name="HS Cohort", version="v1", modality="MRI", source="Clinical", subject_count=120, hpc_root_path="./sample_data/hs", manifest_path="./sample_data/hs/manifest.csv", label_schema="segmentation", qc_status="Validated", benchmark_enabled=True, description="Curated hippocampal sclerosis benchmark dataset"),
                    Dataset(code="FCD", name="FCD Dataset", disease_group="Focal Cortical Dysplasia", collection_name="FCD Cohort", version="v1", modality="MRI", source="Clinical", subject_count=214, hpc_root_path="./sample_data/fcd", manifest_path="./sample_data/fcd/manifest.csv", label_schema="lesion_mask", qc_status="Validated", benchmark_enabled=True, description="FCD biomarker evaluation cohort"),
                    Dataset(code="AD", name="Alzheimer Dataset", disease_group="Alzheimer", collection_name="AD Cohort", version="v2", modality="MRI", source="ADNI", subject_count=300, hpc_root_path="./sample_data/ad", manifest_path="./sample_data/ad/manifest.csv", label_schema="classification", qc_status="Curated", benchmark_enabled=True, description="Alzheimer benchmarking dataset"),
                    Dataset(code="EEG", name="Epilepsy EEG Dataset", disease_group="Epilepsy", collection_name="EEG Cohort", version="v1", modality="EEG", source="Clinical", subject_count=85, hpc_root_path="./sample_data/eeg", manifest_path="./sample_data/eeg/manifest.csv", label_schema="classification", qc_status="Curated", benchmark_enabled=True, description="Epilepsy EEG cohort"),
                ]
            )
            db.commit()

        if not db.query(Pipeline).first():
            db.add_all(
                [
                    Pipeline(
                        name="hippocampal-sclerosis-detector",
                        title="Hippocampal Sclerosis Detector",
                        image="registry/biomarkers/hs-detector:0.9",
                        modality="MRI",
                        description="Initial seeded biomarker pipeline",
                        yaml_definition="name: hippocampal-sclerosis-detector\nimage: registry/biomarkers/hs-detector:0.9\n",
                    ),
                    Pipeline(
                        name="tbi-lesion-detector",
                        title="TBI Lesion Detector",
                        image="registry/brain/tbi-lesion:1.1",
                        modality="MRI",
                        description="Initial seeded TBI detector",
                        yaml_definition="name: tbi-lesion-detector\nimage: registry/brain/tbi-lesion:1.1\n",
                    ),
                ]
            )
            db.commit()

        if not db.query(EvaluationRequest).first():
            pipeline_1 = db.query(Pipeline).filter(Pipeline.name == "hippocampal-sclerosis-detector").first()
            pipeline_2 = db.query(Pipeline).filter(Pipeline.name == "tbi-lesion-detector").first()
            dataset_1 = db.query(Dataset).filter(Dataset.name == "HS Dataset").first()
            dataset_2 = db.query(Dataset).filter(Dataset.name == "FCD Dataset").first()
            dataset_3 = db.query(Dataset).filter(Dataset.name == "Epilepsy EEG Dataset").first()
            db.add_all(
                [
                    EvaluationRequest(request_code="REQ-1042", pipeline_id=pipeline_1.id, dataset_id=dataset_1.id, description="Evaluate hippocampal biomarker pipeline", status="processing", report_status="pending", admin_note="Running on GPU node."),
                    EvaluationRequest(request_code="REQ-1041", pipeline_id=pipeline_2.id, dataset_id=dataset_2.id, description="Validate lesion detector on open dataset", status="reporting", report_status="preparing", admin_note="Report package in preparation."),
                    EvaluationRequest(request_code="REQ-1038", pipeline_id=pipeline_1.id, dataset_id=dataset_3.id, description="Completed archived run", status="completed", report_status="ready", admin_note="Completed successfully."),
                ]
            )
            db.commit()

        if not db.query(Report).first():
            completed_request = db.query(EvaluationRequest).filter(EvaluationRequest.request_code == "REQ-1038").first()
            if completed_request:
                db.add(
                    Report(
                        request_id=completed_request.id,
                        status="ready",
                        pdf_path=f"reports/{completed_request.request_code}.pdf",
                        json_path=f"reports/{completed_request.request_code}.json",
                        csv_path=f"reports/{completed_request.request_code}.csv",
                    )
                )
                db.commit()

        if not db.query(HPCConnection).first():
            db.add(HPCConnection(hostname="hpc.example.org", username="researcher", port=22, notes="Seeded mock HPC connection", status="connected", is_active=True))
            db.commit()
    finally:
        db.close()


def _ensure_meld_and_ideas_catalog(db) -> None:
    """
    Register MELD Graph + IDEAS (Atlas) on Veritas for all users (idempotent).
    GET /api/v1/pipelines and dataset catalog include these; Atlas dataset_id remains `ideas`.

    Always refreshes `meld-graph-fcd` from `_MELD_GRAPH_FCD_YAML` so upgrades pick up the MELD plugin block.
    """
    meld = db.query(Pipeline).filter(Pipeline.name == "meld-graph-fcd").first()
    if meld:
        meld.title = _MELD_GRAPH_FCD_TITLE
        meld.image = _MELD_GRAPH_FCD_IMAGE
        meld.modality = "MRI"
        meld.description = _MELD_GRAPH_FCD_DESCRIPTION
        meld.yaml_definition = _MELD_GRAPH_FCD_YAML
    else:
        db.add(
            Pipeline(
                name="meld-graph-fcd",
                title=_MELD_GRAPH_FCD_TITLE,
                image=_MELD_GRAPH_FCD_IMAGE,
                modality="MRI",
                description=_MELD_GRAPH_FCD_DESCRIPTION,
                yaml_definition=_MELD_GRAPH_FCD_YAML,
            )
        )
    db.commit()

    if not db.query(Dataset).filter(Dataset.code == "IDEAS").first():
        db.add(
            Dataset(
                code="IDEAS",
                name="ideas",
                disease_group="Epilepsy",
                collection_name="IDEAS",
                version="v1",
                modality="MRI",
                source="Atlas / OOD",
                subject_count=0,
                hpc_root_path="/ood/share/datasets/ideas",
                manifest_path="",
                label_schema="BIDS",
                qc_status="Validated",
                benchmark_enabled=True,
                description=(
                    "Atlas dataset_id `ideas` (IDEAS epilepsy cohort, public). "
                    "Same id for Veritas jobs and POST /atlas/staging/request."
                ),
            )
        )
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    cfg = get_settings()
    validate_production_settings(cfg)
    if cfg.database_auto_create_schema:
        Base.metadata.create_all(bind=engine)
    if cfg.seed_demo_data_on_startup:
        seed_data()
    db = SessionLocal()
    try:
        _ensure_meld_and_ideas_catalog(db)
    finally:
        db.close()
    if cfg.hpc_validate_on_startup and cfg.hpc_mode == "slurm":
        from app.services.hpc_adapter import get_hpc_adapter
        from app.services.hpc_service import HPCConnectionService

        db = SessionLocal()
        try:
            conn = HPCConnectionService.get_active_connection(db)
            if conn is None:
                raise RuntimeError(
                    "HPC_VALIDATE_ON_STARTUP is true but no active HPC connection exists; configure HPC in the admin UI or DB first."
                )
            if not get_hpc_adapter().validate_connection(conn):
                raise RuntimeError(f"HPC SSH validation failed for {conn.hostname!r} (check keys, host, and firewall).")
        finally:
            db.close()
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(LimitRequestBodySizeMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(AuthRateLimitMiddleware)
app.add_middleware(
    SecurityHeadersMiddleware,
    production=(settings.app_env or "").strip().lower() == "production",
)
_th = trusted_hosts_list(settings)
if _th:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=_th)
app.include_router(api_router, prefix=settings.api_v1_prefix)


Path(settings.artifact_root_dir).expanduser().mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(Path(settings.artifact_root_dir).expanduser())), name="static")


@app.get("/health", include_in_schema=False)
def kubernetes_liveness() -> dict:
    """Load balancers / Kubernetes probes (no /api/v1 prefix). Same semantics as GET /api/v1/health."""
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
def kubernetes_readiness():
    """Readiness: DB (+ Redis/S3 when configured). Same as GET /api/v1/ready."""
    return readiness_probe()
