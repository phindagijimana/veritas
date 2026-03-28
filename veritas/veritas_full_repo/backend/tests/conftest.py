"""Tests default to PostgreSQL (see backend README). Set VERITAS_USE_SQLITE_TESTS=1 for SQLite without Docker."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

_ROOT = Path(__file__).resolve().parents[1]

_USE_SQLITE = os.environ.get("VERITAS_USE_SQLITE_TESTS", "").lower() in ("1", "true", "yes")

if _USE_SQLITE:
    _fd, _SQLITE_PATH = tempfile.mkstemp(suffix="veritas_test.db")
    os.close(_fd)
    os.environ["DATABASE_URL"] = f"sqlite:///{_SQLITE_PATH}"
    os.environ["DATABASE_AUTO_CREATE_SCHEMA"] = "true"
else:
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+psycopg://veritas:veritas@127.0.0.1:5433/veritas_test",
    )
    os.environ.setdefault("DATABASE_AUTO_CREATE_SCHEMA", "false")

os.environ["SEED_DEMO_DATA_ON_STARTUP"] = "false"
os.environ.setdefault("HPC_MODE", "mock")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")

from app.core.config import get_settings

get_settings.cache_clear()

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Dataset, EvaluationRequest, HPCConnection, Pipeline, Report
from app.models.enums import ReportStatus, RequestStatus

if _USE_SQLITE:
    TEST_ENGINE = create_engine(
        os.environ["DATABASE_URL"],
        future=True,
        connect_args={"check_same_thread": False},
    )
else:
    TEST_ENGINE = create_engine(
        os.environ["DATABASE_URL"],
        future=True,
        pool_pre_ping=True,
    )

TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autoflush=False,
    autocommit=False,
    future=True,
    class_=Session,
)


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


def _clear_all_rows(engine) -> None:
    url = os.environ.get("DATABASE_URL", "")
    with engine.begin() as conn:
        if url.startswith("sqlite"):
            for table in reversed(Base.metadata.sorted_tables):
                conn.execute(text(f"DELETE FROM {table.name}"))
        else:
            names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
            if names:
                conn.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))


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
def setup_database(request: pytest.FixtureRequest):
    if not _USE_SQLITE:
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=_ROOT,
            check=True,
            env=os.environ.copy(),
        )
    else:
        Base.metadata.create_all(bind=TEST_ENGINE)

    _clear_all_rows(TEST_ENGINE)

    db = TestingSessionLocal()
    try:
        seed_test_data(db)
    finally:
        db.close()
    yield
    TEST_ENGINE.dispose()
    if _USE_SQLITE:
        try:
            os.unlink(_SQLITE_PATH)
        except OSError:
            pass


@pytest.fixture()
def client(setup_database):
    return TestClient(app)
