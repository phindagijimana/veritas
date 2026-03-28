# Block 12 — AuthN / AuthZ (current state)

## Implemented

- **Bearer tokens (dev):** HS256 with `ATLAS_DEV_BEARER_SECRET` when `ATLAS_ENV` is `dev`, `development`, or `local`.
- **OIDC / JWKS (non-dev):** RS256/ES256 validation via `ATLAS_JWKS_URL`, `ATLAS_JWT_ISSUER`, `ATLAS_JWT_AUDIENCE` when dev-JWT mode is off.
- **Internal automation:** `X-Internal-Api-Key` maps to an internal principal (admin-capable for operational routes).
- **Veritas service auth (optional):** `X-Atlas-Client-Id` / `X-Atlas-Client-Secret` when `ATLAS_VERITAS_CLIENT_SECRET` is set.
- **Forwarded principals (dev only):** `X-Principal-*` headers when `ATLAS_ALLOW_FORWARDED_PRINCIPAL=true` — **must be false in production** (enforced by `validate_production_settings`).
- **Authorization:** Policy checks (`app/security/policy.py`) against dataset visibility plus **database-backed** rows in `dataset_permission_grants` (see `app/services/dataset_access.py`).
- **Admin APIs:** Grant lifecycle and audit query under `/api/v1/admin/*` (requires internal/admin principal); see README.

## Security demo routes (`/api/v1/security-demo/*`)

Legacy demo handlers used during Block 12 bring-up. They are **not** required for production integrations.

- Mounted only when `ATLAS_SECURITY_DEMO_ENABLED=true` (must be **false** in production).
- Responses include `Deprecation` and `Warning` headers advising disable in production.

## Production checklist

- Disable `ATLAS_SECURITY_DEMO_ENABLED`.
- Disable `ATLAS_ALLOW_FORWARDED_PRINCIPAL`.
- Use real OIDC issuer/JWKS URLs and non-placeholder secrets (`validate_production_settings`).
