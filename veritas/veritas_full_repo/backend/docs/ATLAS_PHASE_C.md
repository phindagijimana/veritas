# Atlas Phase C

Phase C adds:
- admin/runtime staging status visibility
- mocked Pennsieve-backed staging behavior
- request staging status endpoint
- frontend hooks for prepare/refresh staging

## New endpoints
- `POST /api/v1/atlas-execution/prepare`
- `GET /api/v1/requests/{request_id}/staging-status`

## Frontend expectations
The admin dashboard can:
- prepare Atlas staging
- refresh staging status
- display:
  - atlas staging id
  - manifest url
  - staged dataset path
  - status / message

## Test strategy
Tests use mocked Pennsieve staging behavior so the repo can validate logic
without requiring real Pennsieve access.
