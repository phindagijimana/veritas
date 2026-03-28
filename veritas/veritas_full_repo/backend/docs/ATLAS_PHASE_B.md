
# Veritas Atlas Phase B

Phase B integrates Atlas-governed staging into the HPC execution path.

## What this phase adds

- Atlas approval/staging orchestration service
- job-scoped stage script and env generation
- runtime preamble builder for Slurm/container execution
- new request/job metadata fields for staging lifecycle
- tests with mocked Atlas responses

## Intended flow

1. User selects an Atlas-backed dataset in Veritas.
2. Request is created with `atlas_dataset_id`.
3. Job submission calls Atlas to request staging approval.
4. If approved, Veritas writes:
   - `stage_dataset.sh`
   - `atlas_stage.env`
5. Slurm runtime invokes the staging preamble before pipeline execution.
6. Dataset is staged into a job-specific path and exported as:
   - `VERITAS_STAGED_DATASET_PATH`

## New route

- `POST /api/v1/atlas-execution/prepare`

## Deferred to later phases

- real Pennsieve transfer implementation
- continuous staging-status polling
- automatic cleanup policies
- route wiring into the full live job service
