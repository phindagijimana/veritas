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
