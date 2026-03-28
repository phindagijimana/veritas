"""Optional live integration: Veritas ↔ Atlas over HTTP (no mock).

Requires a running Atlas API with matching Veritas credentials.

Skip unless ATLAS_LIVE_TEST=1. Typical env:

  export ATLAS_LIVE_TEST=1
  export ATLAS_API_BASE_URL=http://127.0.0.1:8000/api/v1
  export ATLAS_API_CLIENT_ID=veritas
  export ATLAS_API_CLIENT_SECRET=<same as Atlas ATLAS_VERITAS_CLIENT_SECRET>

Optional second check (Veritas process with ATLAS_INTEGRATION_MODE=live):

  export VERITAS_LIVE_BASE_URL=http://127.0.0.1:6000
  pytest tests/integration/test_atlas_live_integration.py -m integration -v
"""

from __future__ import annotations

import os

import httpx
import pytest

pytestmark = pytest.mark.integration


def _live_enabled() -> bool:
    return os.environ.get("ATLAS_LIVE_TEST", "").lower() in ("1", "true", "yes")


def _skip_reason_atlas_url() -> str | None:
    base = (os.environ.get("ATLAS_API_BASE_URL") or "").strip().rstrip("/")
    if not base:
        return "Set ATLAS_API_BASE_URL (e.g. http://127.0.0.1:8000/api/v1)"
    if "example.org" in base.lower() or "atlas.example" in base.lower():
        return "Set ATLAS_API_BASE_URL to your running Atlas (not example.org)"
    return None


def _skip_reason_secret() -> str | None:
    secret = (os.environ.get("ATLAS_API_CLIENT_SECRET") or "").strip()
    if not secret or secret.lower() in ("change-me", "changeme"):
        return "Set ATLAS_API_CLIENT_SECRET to match Atlas ATLAS_VERITAS_CLIENT_SECRET"
    return None


@pytest.mark.integration
def test_atlas_live_list_datasets_with_veritas_headers() -> None:
    """GET Atlas /datasets using X-Atlas-Client-* (same path Veritas AtlasClient uses)."""
    if not _live_enabled():
        pytest.skip("Set ATLAS_LIVE_TEST=1 to run live Atlas HTTP tests")

    skip = _skip_reason_atlas_url()
    if skip:
        pytest.skip(skip)
    skip = _skip_reason_secret()
    if skip:
        pytest.skip(skip)

    base = os.environ["ATLAS_API_BASE_URL"].strip().rstrip("/")
    client_id = os.environ.get("ATLAS_API_CLIENT_ID", "veritas").strip() or "veritas"
    secret = os.environ["ATLAS_API_CLIENT_SECRET"].strip()

    with httpx.Client(timeout=30.0) as client:
        r = client.get(
            f"{base}/datasets",
            headers={
                "X-Atlas-Client-Id": client_id,
                "X-Atlas-Client-Secret": secret,
            },
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) >= 1
    first = body["data"][0]
    assert "atlas_dataset_id" in first
    assert first.get("name")


@pytest.mark.integration
def test_veritas_proxy_lists_atlas_datasets_when_veritas_running() -> None:
    """GET Veritas /api/v1/atlas/datasets (AtlasClient live inside Veritas)."""
    if not _live_enabled():
        pytest.skip("Set ATLAS_LIVE_TEST=1 to run live integration tests")

    veritas_base = (os.environ.get("VERITAS_LIVE_BASE_URL") or "").strip().rstrip("/")
    if not veritas_base:
        pytest.skip("Set VERITAS_LIVE_BASE_URL (e.g. http://127.0.0.1:6000) to test Veritas proxy")

    skip = _skip_reason_atlas_url()
    if skip:
        pytest.skip(skip)
    skip = _skip_reason_secret()
    if skip:
        pytest.skip(skip)

    with httpx.Client(timeout=45.0) as client:
        r = client.get(f"{veritas_base}/api/v1/atlas/datasets")

    assert r.status_code == 200, r.text
    payload = r.json()
    assert "data" in payload
    data = payload["data"]
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "atlas_dataset_id" in data[0]
