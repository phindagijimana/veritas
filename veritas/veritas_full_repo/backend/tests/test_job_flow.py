def test_submit_job_returns_scheduler_identifier(client):
    payload = {
        "job_name": "eval-job",
        "pipeline": "registry/biomarkers/hs-detector:0.9",
        "dataset": "FCD Dataset",
        "partition": "gpu",
        "resources": {
            "preset": "1 GPU • 16 CPU • 64 GB RAM",
            "gpu": 1,
            "cpu": 16,
            "memory_gb": 64,
            "wall_time": "08:00:00",
            "constraint": "",
            "sbatch_overrides": "",
        },
    }
    response = client.post("/api/v1/jobs/submit/REQ-2003", json=payload)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["scheduler_job_id"]
    assert data["status"].lower() in {"created", "queued", "running", "completed"}


def test_submit_meld_pipeline_requires_subject(client):
    payload = {
        "job_name": "meld-ideas",
        "pipeline": "meldproject/meld_graph:latest",
        "dataset": "ideas",
        "partition": "gpu",
        "runtime_profile": "meld_graph",
        "resources": {
            "gpu": 1,
            "cpu": 16,
            "memory_gb": 64,
            "wall_time": "24:00:00",
        },
    }
    r = client.post("/api/v1/jobs/submit/REQ-2003", json=payload)
    assert r.status_code == 400
    assert "meld_subject_id" in r.json()["detail"]


def test_submit_meld_pipeline_ok(client):
    payload = {
        "job_name": "meld-ideas",
        "pipeline": "meldproject/meld_graph:latest",
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
    r = client.post("/api/v1/jobs/submit/REQ-2003", json=payload)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["scheduler_job_id"]
