from __future__ import annotations

"""
Patch-style reference model changes for Veritas phase A.

Add these fields to your real SQLAlchemy models.

EvaluationRequest:
    atlas_dataset_id
    atlas_dataset_version
    dataset_source
    dataset_access_status

Job:
    atlas_staging_id
    staging_status
    staged_dataset_path
    staging_started_at
    staging_completed_at
    staging_credentials_ref
    atlas_manifest_ref
"""

REQUEST_FIELDS = [
    ("atlas_dataset_id", "String", True),
    ("atlas_dataset_version", "String", True),
    ("dataset_source", "String", False),
    ("dataset_access_status", "String", False),
]

JOB_FIELDS = [
    ("atlas_staging_id", "String", True),
    ("staging_status", "String", False),
    ("staged_dataset_path", "String", True),
    ("staging_started_at", "DateTime", True),
    ("staging_completed_at", "DateTime", True),
    ("staging_credentials_ref", "String", True),
    ("atlas_manifest_ref", "String", True),
]
