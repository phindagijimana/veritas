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

## CLI

From the **validator monorepo root**, use **`./api install`**, **`./api start`**, etc. (see repo `README.md`).

From the `atlas_api_app` directory after `pip install -e .`:

```bash
atlas-api --help
atlas-api serve --host 0.0.0.0 --port 8000          # default if you omit the subcommand
atlas-api dev-token --sub alice --roles researcher,admin
python -m app --help                                 # same entry points
```

Environment overrides: `ATLAS_HOST`, `ATLAS_PORT`. The legacy script `python scripts/generate_dev_token.py` still works and forwards to `dev-token`.

## Database (PostgreSQL)

The default **`ATLAS_DATABASE_URL`** targets local Postgres:  
`postgresql+psycopg2://atlas:atlas@127.0.0.1:5432/atlas_dev` (see `.env.example`).

**Local database** (Docker):

```bash
cd atlas_api_app
docker compose up -d
cp .env.example .env   # optional; adjust secrets
export ATLAS_DATABASE_AUTO_CREATE_SCHEMA=false
python -m alembic upgrade head
```

**Tests** default to PostgreSQL database **`atlas_test`** (`tests/conftest.py`). The compose file creates `atlas_test` via `docker/initdb/`. Run **`docker compose up -d`** before **`pytest`**.

Quick runs without Docker: **`ATLAS_USE_SQLITE_TESTS=1 pytest`** (SQLite file + Alembic; CI still uses Postgres).

## Database migrations (production)

Set `ATLAS_DATABASE_AUTO_CREATE_SCHEMA=false` and apply schema with Alembic before starting the app:

```bash
cd atlas_api_app
export ATLAS_DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/atlas"
python -m alembic upgrade head
```

SQLite is only supported for ad-hoc use; production validation rejects it when `ATLAS_ENV=production`. If **`ATLAS_VERITAS_CLIENT_SECRET`** is empty in production, startup logs a **warning** (Veritas `X-Atlas-Client-*` auth stays disabled). See `tests/unit/test_bootstrap_veritas_warning.py`.

- **`001_initial`** — explicit `CREATE TABLE` / indexes (reviewable, reversible via `alembic downgrade`).
- **`002_audit_ops`** — idempotent deltas for older DBs that predate the current `001` (audit table and staging retry/export columns). Fresh installs typically skip work here.

Run `alembic upgrade head` after pulling. For pinned dependencies, see `requirements-lock.txt` and `docs/operations.md`.

## Admin: dataset grants and audit

Internal or admin principals (`X-Internal-Api-Key` or bearer with `admin` role) can manage **`dataset_permission_grants`**:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/admin/grants` | List grants (optional `?dataset_id=`). |
| POST | `/api/v1/admin/grants` | Create grant (`dataset_id`, `principal_type`, `principal_id`, `access_level`). |
| PATCH | `/api/v1/admin/grants/{id}` | Update `access_level`. |
| DELETE | `/api/v1/admin/grants/{id}` | Revoke grant. |
| GET | `/api/v1/admin/audit-events` | Recent audit rows (`grant.*`, `staging.manifest.*`). |

See `docs/operations.md` for metrics, rate limits, and secret rotation.
