def test_requests_list_contract(client):
    response = client.get("/api/v1/requests")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    assert body["data"][0]["id"].startswith("REQ-")
    assert "current_phase" in body["data"][0]


def test_dataset_registry_contract(client):
    response = client.get("/api/v1/datasets")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    item = body["data"][0]
    assert {"code", "name", "disease_group", "version", "subject_count"}.issubset(item.keys())


def test_hpc_summary_contract(client):
    response = client.get("/api/v1/hpc/summary")
    assert response.status_code == 200
    summary = response.json()["data"]
    assert set(summary.keys()) >= {"status", "queued", "running", "gpu_free", "hpc_mode"}
