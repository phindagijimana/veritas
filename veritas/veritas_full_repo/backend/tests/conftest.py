import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

# Ensure app config reads a test sqlite DB before importing app/session modules.
TEST_DB_PATH = Path(__file__).resolve().parent / "test_step5.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["HPC_MODE"] = "mock"
os.environ.setdefault("APP_ENV", "development")

from app.core.config import get_settings

get_settings.cache_clear()

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Dataset, EvaluationRequest, HPCConnection, Pipeline, Report
from app.models.enums import ReportStatus, RequestStatus

TEST_ENGINE = create_engine(
    f"sqlite:///{TEST_DB_PATH.as_posix()}",
    future=True,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False, future=True, class_=Session)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def reset_cached_settings_after_each_test():
    yield
    get_settings.cache_clear()


def seed_test_data(db: Session) -> None:
    fcd = Dataset(
        code="FCD",
        name="FCD Dataset",
        disease_group="Epilepsy",
        collection_name="FCD Cohort",
        version="v1",
        modality="MRI",
        source="Clinical",
        subject_count=214,
        hpc_root_path="/datasets/fcd/v1",
        manifest_path="/datasets/fcd/v1/manifest.json",
        label_schema="lesion_mask",
        qc_status="Validated",
        benchmark_enabled=True,
    )
    hs = Dataset(
        code="HS",
        name="HS Dataset",
        disease_group="Hippocampal Sclerosis",
        collection_name="HS Cohort",
        version="v1",
        modality="MRI",
        source="Clinical",
        subject_count=180,
        hpc_root_path="/datasets/hs/v1",
        manifest_path="/datasets/hs/v1/manifest.json",
        label_schema="prediction_json",
        qc_status="Curated",
        benchmark_enabled=True,
    )
    pipeline = Pipeline(
        name="hs-detector",
        title="HS Detector",
        image="registry/biomarkers/hs-detector:0.9",
        modality="MRI",
        description="Seeded test pipeline",
        yaml_definition="name: hs-detector\nimage: registry/biomarkers/hs-detector:0.9\n",
    )
    db.add_all([fcd, hs, pipeline])
    db.flush()

    req_processing = EvaluationRequest(
        request_code="REQ-2001",
        description="Processing request",
        pipeline_id=pipeline.id,
        dataset_id=fcd.id,
        status=RequestStatus.processing.value,
        report_status=ReportStatus.preparing.value,
        admin_note="Running",
    )
    req_reporting = EvaluationRequest(
        request_code="REQ-2002",
        description="Reporting request",
        pipeline_id=pipeline.id,
        dataset_id=hs.id,
        status=RequestStatus.reporting.value,
        report_status=ReportStatus.preparing.value,
        admin_note="Metrics ready",
    )
    req_submitted = EvaluationRequest(
        request_code="REQ-2003",
        description="Submitted request",
        pipeline_id=pipeline.id,
        dataset_id=hs.id,
        status=RequestStatus.submitted.value,
        report_status=ReportStatus.pending.value,
        admin_note="Awaiting prep",
    )
    # Isolated from REQ-2003 (mutated by job-flow tests) for phase transition tests.
    req_phase_tests = EvaluationRequest(
        request_code="REQ-2090",
        description="State machine tests only",
        pipeline_id=pipeline.id,
        dataset_id=hs.id,
        status=RequestStatus.submitted.value,
        report_status=ReportStatus.pending.value,
        admin_note="Unchanged by job submit tests",
    )
    db.add_all([req_processing, req_reporting, req_submitted, req_phase_tests])
    db.flush()

    db.add(
        Report(
            request_id=req_reporting.id,
            status=ReportStatus.preparing.value,
            pdf_path=f"reports/{req_reporting.request_code}/report.pdf",
            json_path=f"reports/{req_reporting.request_code}/metrics.json",
            csv_path=f"reports/{req_reporting.request_code}/results.csv",
        )
    )
    db.add(
        HPCConnection(
            hostname="hpc.example.org",
            username="tester",
            port=22,
            notes="Test HPC",
            status="connected",
            is_active=True,
        )
    )
    db.commit()


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    Base.metadata.create_all(bind=TEST_ENGINE)
    db = TestingSessionLocal()
    try:
        seed_test_data(db)
    finally:
        db.close()
    yield
    TEST_ENGINE.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture()
def client(setup_database):
    return TestClient(app)
