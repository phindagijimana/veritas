# Veritas Atlas Phase D

This repo package contains:
- mocked Pennsieve transfer execution
- staging validation endpoints
- transfer log exposure
- migration scaffold
- tests and smoke-test script

This package is compile-tested here and designed to be merged into the main Veritas repo.

## Database (PostgreSQL)

Defaults use **`postgresql+psycopg://`** (see `psycopg[binary]` in `requirements.txt`). Local dev DB is **`veritas_dev`** on **`127.0.0.1:5433`** (compose maps host **5433** → container 5432 so another Postgres stack, e.g. Atlas on 5432, can run side by side).

```bash
docker compose up -d
cp .env.example .env   # adjust secrets
python -m alembic upgrade head
```

**Tests** default to database **`veritas_test`** on the same host/port. Run **`docker compose up -d`** before **`pytest`**.

Without Docker: **`VERITAS_USE_SQLITE_TESTS=1 pytest`** uses a temporary SQLite file and `create_all` (CI should use Postgres).

To exclude optional live HTTP tests (default: they skip unless enabled):

```bash
pytest -m "not integration"
```

Production guardrails are enforced in code (`validate_production_settings`): in **`APP_ENV=production`** with **`ATLAS_INTEGRATION_MODE=live`**, **`ATLAS_API_BASE_URL`** must not use placeholder hosts such as **`atlas.example.org`**. Unit tests: `tests/unit/test_production_validation.py`.

## Atlas API (live integration)

With **`ATLAS_INTEGRATION_MODE=live`**, Veritas calls a real Atlas at **`ATLAS_API_BASE_URL`** (must end with `/api/v1`). Set **`ATLAS_API_CLIENT_SECRET`** to the same value as Atlas **`ATLAS_VERITAS_CLIENT_SECRET`**.

**Smoke script** (curl Atlas `/ready` and `/api/v1/datasets` with Veritas headers):

```bash
export ATLAS_VERITAS_CLIENT_SECRET='shared-secret'   # same as Atlas + Veritas env
./scripts/smoke_atlas_live.sh http://127.0.0.1:8000
```

**Pytest** (starts nothing; requires Atlas and optionally Veritas already running):

```bash
export ATLAS_LIVE_TEST=1
export ATLAS_API_BASE_URL=http://127.0.0.1:8000/api/v1
export ATLAS_API_CLIENT_ID=veritas
export ATLAS_API_CLIENT_SECRET='shared-secret'
pytest tests/integration/test_atlas_live_integration.py -m integration -v
# Optional: also exercise Veritas proxy
export VERITAS_LIVE_BASE_URL=http://127.0.0.1:6000
# Veritas process must use ATLAS_INTEGRATION_MODE=live and matching Atlas URL/secret
pytest tests/integration/test_atlas_live_integration.py -m integration -v
```

## CLI

From the **validator monorepo root**, use **`./platform install`**, **`./platform start`**, etc. (see repo `README.md`).

From this directory:

```bash
pip install -e .
python -m alembic upgrade head
veritas-api --help
veritas-api serve --host 0.0.0.0 --port 6000
python -m app --help
```

If you omit the subcommand, **`serve`** is assumed (e.g. `veritas-api --port 6000`). Environment overrides: `VERITAS_HOST`, `VERITAS_PORT`.

Production containers often use `uvicorn app.main:app` directly; the CLI is equivalent for local runs.
