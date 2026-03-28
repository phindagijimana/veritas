from __future__ import annotations

from typing import Any

from app.models.dataset import AtlasDataset, dataset_storage_homes


def _disease_group(row: AtlasDataset) -> str:
    did = (row.dataset_id or "").lower()
    # IDEAS + CIDUR_BIDS: both epilepsy cohorts (CIDUR is additionally hospital clinical / protected in Atlas).
    if did.startswith("ideas") or "cidur" in did:
        return "Epilepsy"
    if row.access_class == "validation":
        return "Clinical"
    if row.access_class == "training":
        return "Research"
    return "General"


def _veritas_dataset_metadata(row: AtlasDataset) -> dict[str, Any]:
    did = (row.dataset_id or "").lower()
    meta: dict[str, Any] = {
        "visibility": row.visibility,
        "access_class": row.access_class,
        "storage_homes": dataset_storage_homes(row),
        "epilepsy_cohort": did.startswith("ideas") or "cidur" in did,
    }
    if "cidur" in did:
        meta["clinical_hospital_data"] = True
        meta["requires_grant_for_api_access"] = row.visibility == "restricted"
    return meta


def _dataset_description(row: AtlasDataset) -> str:
    did = (row.dataset_id or "").lower()
    if did.startswith("ideas"):
        return (
            "IDEAS epilepsy open cohort; Pennsieve catalog + durable copy on OOD. "
            "Public in Atlas for discovery and pipelines."
        )
    if "cidur" in did:
        return (
            "CIDUR BIDS epilepsy clinical (hospital) cohort on OOD; Pennsieve + OOD mirror. "
            "Protected in Atlas — access via grants only."
        )
    return f"Atlas dataset {row.dataset_id} ({row.visibility})"


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
            "description": _dataset_description(row),
            "subject_count": 42 if row.visibility == "public" else None,
            "manifest_ref": manifest_ref,
            "labels_available": row.access_class == "validation",
            "metadata": _veritas_dataset_metadata(row),
        }
    )
    return detail
