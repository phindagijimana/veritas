# Block 12 - AuthN/AuthZ Hardening

## Goals
- move from header-only trust to real bearer-token validation
- support OIDC/JWKS in non-dev environments
- preserve internal service-to-service API key support
- centralize authorization in a policy layer

## Modes
- dev: HS256 local bearer tokens for fast development
- prod/staging: OIDC/JWKS token validation
- internal: X-Internal-Api-Key for service automation

## Authorization model
Policy evaluation uses:
- principal
- action
- resource context
- explicit grants
- dataset visibility

## Recommendation for next block
Replace demo endpoints with wired authorization checks against real dataset records and permission tables.
