from __future__ import annotations

from fastapi import HTTPException, status

from app.core.enums import DatasetVisibility
from app.models.dataset import AtlasDataset


def ensure_stage_allowed(row: AtlasDataset, compute_target: str) -> str:
    """
    Validates staging policy for a dataset and compute target.
    Returns Atlas mode: public_download_or_cache or controlled_validation_staging.
    """
    if not row.staging_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This dataset is not eligible for controlled staging.",
        )
    targets = list(row.allowed_compute_targets or [])
    if compute_target not in targets:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compute target is not approved for this dataset.",
        )
    if row.visibility == DatasetVisibility.PUBLIC.value:
        return "public_download_or_cache"
    return "controlled_validation_staging"
