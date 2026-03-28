from app.services.request_service import RequestService


def test_request_service_transition_rules():
    assert RequestService.can_transition("submitted", "pipeline_prep") is True
    assert RequestService.can_transition("submitted", "completed") is False
    assert RequestService.can_transition("reporting", "completed") is True
