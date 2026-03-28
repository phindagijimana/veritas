# Atlas Phase D

Phase D adds a mocked execution path for Pennsieve transfer plus staging validation.

## Added capabilities
- execute Pennsieve-backed staging
- cache request staging status
- validate the staged dataset contents
- expose transfer log + validation status to the frontend

## Endpoints
- `POST /api/v1/atlas-execution/execute-stage`
- `POST /api/v1/requests/{request_id}/staging-validate`
- `GET /api/v1/requests/{request_id}/staging-status`

## Frontend integration
The admin HPC staging card can now:
- prepare Atlas staging
- validate staged dataset
- show transfer log
- show staged dataset path
- show validation status

## Testing
This package includes mocked service and API tests so the staging lifecycle can be validated without real Pennsieve/HPC access.
