# Veritas Atlas Phase A

Phase A implements the first integration layer between Veritas and Atlas/Pennsieve-governed datasets.

## Included in Phase A
- Atlas API client
- Atlas dataset/staging schemas
- Dataset staging service
- Alembic migration for Atlas/staging metadata
- Atlas API routes for testing and integration
- Unit tests for staging-plan construction

## Expected data flow
1. User selects dataset in Veritas
2. Veritas requests staging approval from Atlas
3. Atlas returns short-lived credentials and a staging manifest
4. Veritas builds a job-specific staging plan
5. HPC job stages the dataset into a request-scoped workspace
6. Pipeline runtime later consumes the staged dataset path

## New metadata tracked

### evaluation_requests
- atlas_dataset_id
- atlas_dataset_version
- dataset_source
- dataset_access_status

### jobs
- atlas_staging_id
- staging_status
- staged_dataset_path
- staging_started_at
- staging_completed_at
- staging_credentials_ref
- atlas_manifest_ref

## What is intentionally not included yet
- Full Pennsieve file download implementation
- Real HPC/Slurm pre-run execution wiring
- Atlas approval UI
- Background staging retries
