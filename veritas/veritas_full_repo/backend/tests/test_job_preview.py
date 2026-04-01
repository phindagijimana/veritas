"""Job preview: Slurm + MELD runtime without submit (Veritas platform)."""

from __future__ import annotations

import pytest

from app.core.config import get_settings


def _meld_payload():
    return {
        "job_name": "meld-ideas-preview",
        "pipeline": "docker.io/phindagijimana321/meld_graph:v2.2.4-nir2",
        "dataset": "ideas",
        "partition": "gpu",
        "runtime_profile": "meld_graph",
        "meld_subject_id": "sub-01",
        "meld_session": None,
        "staged_dataset_path": None,
        "resources": {
            "gpu": 1,
            "cpu": 16,
            "memory_gb": 64,
            "wall_time": "24:00:00",
        },
    }


def test_preview_meld_returns_sbatch_and_pipeline_script(client, monkeypatch):
    monkeypatch.setenv("RUNTIME_ENGINE", "apptainer")
    get_settings.cache_clear()
    r = client.post("/api/v1/jobs/preview/REQ-2090", json=_meld_payload())
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["runtime_engine"] == "apptainer"
    assert data["hpc_mode"] == "mock"
    assert "apptainer exec --cleanenv" in data["pipeline_runtime_script"]
    assert "docker://" in data["pipeline_runtime_script"]
    assert "# Veritas runtime_engine=apptainer" in data["sbatch_script"]
    assert "printf '%s'" in data["sbatch_script"]  # base64 embed


def test_preview_meld_requires_subject(client):
    payload = _meld_payload()
    del payload["meld_subject_id"]
    r = client.post("/api/v1/jobs/preview/REQ-2090", json=payload)
    assert r.status_code == 400
    assert "meld_subject_id" in r.json()["detail"]


def test_preview_meld_batch_subject_ids_without_single(client, monkeypatch):
    monkeypatch.setenv("RUNTIME_ENGINE", "apptainer")
    get_settings.cache_clear()
    payload = _meld_payload()
    del payload["meld_subject_id"]
    payload["meld_subject_ids"] = ["sub-01", "sub-02"]
    r = client.post("/api/v1/jobs/preview/REQ-2090", json=payload)
    assert r.status_code == 200, r.text
    pr = r.json()["data"]["pipeline_runtime_script"]
    assert "sub-01" in pr
    assert "sub-02" in pr
    assert "SUBJECTS=(" in pr


def test_preview_unknown_request(client):
    r = client.post("/api/v1/jobs/preview/REQ-99999", json=_meld_payload())
    assert r.status_code == 404
