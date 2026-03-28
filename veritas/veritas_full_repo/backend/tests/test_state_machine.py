def test_invalid_phase_transition_returns_409(client):
    response = client.patch(
        "/api/v1/requests/REQ-2090/status",
        json={"current_phase": "Completed", "admin_note": "skip ahead"},
    )
    assert response.status_code == 409
    assert "Invalid request phase transition" in response.json()["detail"]


def test_valid_phase_transition_succeeds(client):
    response = client.patch(
        "/api/v1/requests/REQ-2090/status",
        json={"current_phase": "Pipeline Prep", "admin_note": "prep started"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["current_phase"] == "Pipeline Prep"
    assert data["admin_note"] == "prep started"
