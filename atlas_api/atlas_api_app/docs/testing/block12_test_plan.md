# Block 12 Test Plan

## Unit
- policy decisions for public vs restricted datasets
- write/admin permission escalation
- bearer token decoding in dev mode

## Integration
- auth rejection on missing credentials
- internal API key access to admin endpoints
- forwarded service headers for trusted gateway scenarios

## Next E2E
- restricted dataset read with DB-backed permission grants
- execution contract authorization path
- admin audit route auth coverage
