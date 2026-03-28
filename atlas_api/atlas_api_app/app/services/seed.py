from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import AccessLevel
from app.models.dataset import AtlasDataset
from app.models.dataset_grant import DatasetPermissionGrant

DEMO_DATASETS: list[dict] = [
    # --- Epilepsy cohorts with data already on OOD: IDEAS (open) + CIDUR_BIDS (hospital clinical, protected) ---
    # Primary home: Pennsieve; secondary: OOD path where full copies already exist for staging/compute.
    # IDEAS: open epilepsy; Atlas lists publicly so pipelines can attach without a grant.
    {
        "dataset_id": "ideas",
        "name": "IDEAS (epilepsy — open cohort, OOD + Pennsieve)",
        "visibility": "public",
        "access_class": "training",
        "storage_provider": "pennsieve",
        "canonical_source": "pennsieve",
        "download_url": None,
        "staging_allowed": True,
        "allowed_compute_targets": ["URMC_HPC", "OOD_HPC", "REMOTE_SERVER"],
        "pennsieve_package_id": None,
        "secondary_storage_provider": "ood_hpc",
        "secondary_canonical_source": "ood_hpc",
        "secondary_location_ref": "/ood/share/datasets/ideas",
    },
    # CIDUR_BIDS: epilepsy hospital clinical BIDS on OOD; same disease domain as IDEAS; Atlas restricts reads/downloads to grants.
    {
        "dataset_id": "cidur-bids",
        "name": "CIDUR BIDS (epilepsy clinical hospital — protected, OOD + Pennsieve)",
        "visibility": "restricted",
        "access_class": "validation",
        "storage_provider": "pennsieve",
        "canonical_source": "pennsieve",
        "download_url": None,
        "staging_allowed": True,
        "allowed_compute_targets": ["URMC_HPC", "OOD_HPC"],
        "pennsieve_package_id": None,
        "secondary_storage_provider": "ood_hpc",
        "secondary_canonical_source": "ood_hpc",
        "secondary_location_ref": "/ood/secure/clinical/cidur-bids",
    },
    {
        "dataset_id": "openneuro-ds1",
        "name": "OpenNeuro DS1",
        "visibility": "public",
        "access_class": "training",
        "storage_provider": "pennsieve",
        "canonical_source": "pennsieve",
        "download_url": "https://example.org/downloads/openneuro-ds1.zip",
        "staging_allowed": True,
        "allowed_compute_targets": ["URMC_HPC", "REMOTE_SERVER"],
        "pennsieve_package_id": None,
    },
    {
        "dataset_id": "clinical-mri-a",
        "name": "Clinical MRI A",
        "visibility": "restricted",
        "access_class": "validation",
        "storage_provider": "pennsieve",
        "canonical_source": "pennsieve",
        "download_url": None,
        "staging_allowed": True,
        "allowed_compute_targets": ["URMC_HPC"],
        "pennsieve_package_id": None,
    },
    {
        "dataset_id": "internal-hs-private",
        "name": "Internal HS Private",
        "visibility": "private",
        "access_class": "internal",
        "storage_provider": "pennsieve",
        "canonical_source": "pennsieve",
        "download_url": None,
        "staging_allowed": False,
        "allowed_compute_targets": [],
        "pennsieve_package_id": None,
    },
]

# Demo grant: integration tests use X-Principal-Id user-123 on restricted dataset.
DEMO_GRANTS: list[dict] = [
    {
        "dataset_id": "clinical-mri-a",
        "principal_type": "user",
        "principal_id": "user-123",
        "access_level": AccessLevel.WRITE.value,
    },
]


def seed_demo_datasets_if_empty(db: Session) -> None:
    n = db.scalar(select(func.count()).select_from(AtlasDataset))
    if n and n > 0:
        return
    for row in DEMO_DATASETS:
        db.add(AtlasDataset(**row))
    db.commit()


def seed_demo_grants_if_empty(db: Session) -> None:
    n = db.scalar(select(func.count()).select_from(DatasetPermissionGrant))
    if n and n > 0:
        return
    for row in DEMO_GRANTS:
        db.add(DatasetPermissionGrant(**row))
    db.commit()
