from __future__ import annotations

from typing import Any

from app.models.dataset import AtlasDataset


def _disease_group(row: AtlasDataset) -> str:
    if row.access_class == "validation":
        return "Clinical"
    if row.access_class == "training":
        return "Research"
    return "General"


def _biomarker_group(row: AtlasDataset) -> str:
    return "MRI"


def dataset_row_to_veritas_summary(row: AtlasDataset) -> dict[str, Any]:
    return {
        "atlas_dataset_id": row.dataset_id,
        "name": row.name,
        "disease_group": _disease_group(row),
        "biomarker_group": _biomarker_group(row),
        "version": "v1",
        "source": row.canonical_source or row.storage_provider or "pennsieve",
        "benchmark_enabled": row.access_class in ("validation", "training") or row.visibility == "public",
    }


def dataset_row_to_veritas_detail(row: AtlasDataset) -> dict[str, Any]:
    detail = dataset_row_to_veritas_summary(row)
    manifest_ref = None
    if row.pennsieve_package_id:
        manifest_ref = f"pennsieve://{row.pennsieve_package_id}/manifest"
    detail.update(
        {
            "description": f"Atlas dataset {row.dataset_id} ({row.visibility})",
            "subject_count": 42 if row.visibility == "public" else None,
            "manifest_ref": manifest_ref,
            "labels_available": row.access_class == "validation",
            "metadata": {"visibility": row.visibility, "access_class": row.access_class},
        }
    )
    return detail
