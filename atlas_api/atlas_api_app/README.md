# Veritas Atlas API — Block 12 (Pennsieve-backed)

This repo contains a minimal Atlas API prototype with:
- hybrid auth scaffold
- dataset access policy enforcement
- Pennsieve-backed public dataset downloads
- controlled staging authorization for restricted validation datasets
- frontend landing/admin dashboard prototype under `web/src/`

## Dataset policy
- `public` → downloadable through Atlas
- `restricted` → not directly downloadable, but stageable to approved compute targets
- `private` → internal only

## Pennsieve credentials
Configure these on the Atlas backend or staging service:
- `PENNSIEVE_API_TOKEN`
- `PENNSIEVE_API_SECRET`
- `PENNSIEVE_ORGANIZATION_ID`

These credentials should remain server-side only.

## Database migrations (production)

Set `ATLAS_DATABASE_AUTO_CREATE_SCHEMA=false` and apply schema with Alembic before starting the app:

```bash
cd atlas_api_app
export ATLAS_DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/atlas"
python -m alembic upgrade head
```

For local development, auto-create remains enabled by default; tests use an isolated SQLite file via `tests/conftest.py`.
