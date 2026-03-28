from __future__ import annotations

from typing import Any, Dict, List, Optional

import requests

from app.core.config import get_settings
from app.schemas.atlas import AtlasDatasetDetail, AtlasDatasetSummary, AtlasStagingManifest, AtlasStagingRequest, AtlasStagingResponse


class AtlasClient:
    """
    Thin client for the Atlas governance and staging API.
    Atlas is the control plane that authorizes dataset use and returns
    Pennsieve-backed staging credentials/manifests.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ) -> None:
        cfg = get_settings()
        self.base_url = (base_url or cfg.atlas_api_base_url).rstrip("/")
        self.client_id = client_id or cfg.atlas_api_client_id
        self.client_secret = client_secret or cfg.atlas_api_client_secret
        self.timeout_seconds = timeout_seconds or cfg.atlas_api_timeout_seconds
        self.session = session or requests.Session()

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Atlas-Client-Id": self.client_id,
            "X-Atlas-Client-Secret": self.client_secret,
            "Content-Type": "application/json",
        }

    def _get(self, path: str) -> Any:
        response = self.session.get(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("data", payload)

    def _post(self, path: str, payload: Dict[str, Any]) -> Any:
        response = self.session.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("data", data)

    def list_datasets(self) -> List[AtlasDatasetSummary]:
        payload = self._get("/datasets")
        return [AtlasDatasetSummary(**item) for item in payload]

    def get_dataset(self, atlas_dataset_id: str) -> AtlasDatasetDetail:
        payload = self._get(f"/datasets/{atlas_dataset_id}")
        return AtlasDatasetDetail(**payload)

    def request_staging(self, request: AtlasStagingRequest) -> AtlasStagingResponse:
        payload = self._post("/staging/request", request.dict())
        return AtlasStagingResponse(**payload)

    def get_staging_manifest(self, atlas_staging_id: str) -> AtlasStagingManifest:
        payload = self._get(f"/staging/{atlas_staging_id}/manifest")
        return AtlasStagingManifest(**payload)

    def get_staging_status(self, atlas_staging_id: str) -> AtlasStagingResponse:
        payload = self._get(f"/staging/{atlas_staging_id}")
        return AtlasStagingResponse(**payload)


class MockAtlasClient:
    """In-process Atlas responses for development when ATLAS_INTEGRATION_MODE=mock."""

    def list_datasets(self) -> List[AtlasDatasetSummary]:
        return [
            AtlasDatasetSummary(
                atlas_dataset_id="mock-ds-001",
                name="Mock Epilepsy Cohort",
                disease_group="Epilepsy",
                biomarker_group="MRI",
                version="v1",
                source="pennsieve",
                benchmark_enabled=True,
            )
        ]

    def get_dataset(self, atlas_dataset_id: str) -> AtlasDatasetDetail:
        return AtlasDatasetDetail(
            atlas_dataset_id=atlas_dataset_id,
            name=f"Dataset {atlas_dataset_id}",
            disease_group="Epilepsy",
            biomarker_group="MRI",
            version="v1",
            description="Mock Atlas dataset detail",
            subject_count=42,
            manifest_ref=f"pennsieve://{atlas_dataset_id}/manifest",
            labels_available=True,
        )

    def request_staging(self, request: AtlasStagingRequest) -> AtlasStagingResponse:
        cfg = get_settings()
        manifest_url = f"{cfg.pennsieve_base_url.rstrip('/')}/manifests/{request.atlas_dataset_id}.json"
        return AtlasStagingResponse(
            atlas_staging_id=f"STAGE-MOCK-{request.request_id}",
            atlas_dataset_id=request.atlas_dataset_id,
            status="approved",
            token="mock-staging-token",
            manifest_url=manifest_url,
            source="pennsieve",
        )

    def get_staging_manifest(self, atlas_staging_id: str) -> AtlasStagingManifest:
        return AtlasStagingManifest(
            atlas_staging_id=atlas_staging_id,
            atlas_dataset_id="mock-ds-001",
            files=[{"path": "sub-01/T1w.nii.gz", "size": 1024}],
            dataset_root="/mock/root",
            source="pennsieve",
        )

    def get_staging_status(self, atlas_staging_id: str) -> AtlasStagingResponse:
        return AtlasStagingResponse(
            atlas_staging_id=atlas_staging_id,
            atlas_dataset_id="mock-ds-001",
            status="approved",
            manifest_url=f"{get_settings().pennsieve_base_url.rstrip('/')}/manifests/mock.json",
            source="pennsieve",
        )


def build_atlas_client() -> AtlasClient | MockAtlasClient:
    if get_settings().atlas_integration_mode == "mock":
        return MockAtlasClient()
    return AtlasClient()
