# Validator monorepo

## Local Atlas + Veritas (Docker)

Start **both** Postgres/Redis/MinIO stacks without service-name clashes (separate compose projects):

```bash
chmod +x scripts/dev-stack.sh   # once
./scripts/dev-stack.sh up
./scripts/dev-stack.sh ps
./scripts/dev-stack.sh down
```

**Podman rootless:** if `dev-stack.sh up` reports missing `/etc/subuid`, run **`sudo ./scripts/fix_podman_rootless_subuid.sh`**, then start a new login session. (Not needed for Docker Engine.)

Then run **`alembic upgrade head`** in each app directory (see table below), copy `.env.example` → `.env`, and align **Veritas ↔ Atlas** credentials:

| Setting | Atlas (`atlas_api_app/.env`) | Veritas (`backend/.env`) |
|--------|------------------------------|---------------------------|
| Shared Veritas secret | `ATLAS_VERITAS_CLIENT_SECRET=dev-shared-secret` | `ATLAS_API_CLIENT_SECRET=dev-shared-secret` |
| Live integration | — | `ATLAS_INTEGRATION_MODE=live` |
| Atlas base URL | `ATLAS_PUBLIC_BASE_URL=http://127.0.0.1:8000` | `ATLAS_API_BASE_URL=http://127.0.0.1:8000/api/v1` |

Optional live checks: `ATLAS_LIVE_TEST=1` and `pytest tests/integration/test_atlas_live_integration.py` (Veritas backend).

### Full local run (Docker + migrations + E2E HTTP)

From repo root (shared secret must match on both apps):

```bash
chmod +x scripts/full_local_run.sh scripts/full_local_e2e.py
export ATLAS_VERITAS_CLIENT_SECRET=dev-shared-atlas-veritas-secret
./scripts/full_local_run.sh
# In two more terminals, start ./api and ./platform as printed, then:
export ATLAS_VERITAS_CLIENT_SECRET ATLAS_API_CLIENT_SECRET
python3 scripts/full_local_e2e.py
```

If Atlas and Veritas are already running: `./scripts/full_local_run.sh --e2e-only` (same env vars as below). Use `DATASET_ID=ideas` (default) or another seeded Atlas dataset id.

## `./api` — Atlas API (`atlas_api/atlas_api_app`)

| Command | Description |
|--------|-------------|
| `./api install` | `pip install -e ".[dev]"` (uses `atlas_api_app/.venv` if it exists) |
| `./api venv` | Create `atlas_api_app/.venv` and install editable with dev extras |
| `./api start` | Run the API (`python -m app serve`, default port **8000**) |
| `./api dev-token` | Print an HS256 dev JWT (`--sub`, `--roles`) |
| `./api migrate` | `alembic upgrade head` |
| `./api test` | `pytest` |
| `./api shell` | Python REPL with `app` importable |

Override host/port with `ATLAS_HOST`, `ATLAS_PORT`. Implementation: `bin/api` (root `./api` is a shim).

Legacy: `./atlas` and `bin/atlas` call the same script.

## `./platform` — Veritas backend (`veritas/veritas_full_repo/backend`)

| Command | Description |
|--------|-------------|
| `./platform install` | `pip install -e .` (uses `backend/.venv` if present) |
| `./platform venv` | Create `backend/.venv` and install |
| `./platform start` | Run the API (default port **6000**) |
| `./platform worker` | Celery worker |
| `./platform migrate` | `alembic upgrade head` |
| `./platform test` | `pytest` (expects Postgres; see backend `README.md` / `docker-compose.yml` on port **5433**) |
| `./platform shell` | Python REPL |

Default DB is **PostgreSQL** (`DATABASE_URL` in `.env.example`). Run **`docker compose up -d`** in `veritas/veritas_full_repo/backend` before **`./platform start`** or **`pytest`**. Quick tests without Docker: **`VERITAS_USE_SQLITE_TESTS=1 pytest`**.

Override host/port with `VERITAS_HOST`, `VERITAS_PORT`. Implementation: `bin/platform`.

Legacy: `./vt` and `bin/veritas` call the same script.

**Veritas frontend (product UI):** `veritas/veritas_full_repo/frontend` is a Vite + React app. After `npm install`, run **`npm run dev`** — default URL **http://127.0.0.1:7000**. The demo UI includes IDEAS / MELD catalog copy; the **authoritative** MELD pipeline (`meld-graph-fcd`) is registered by the backend on startup — confirm with **`GET http://127.0.0.1:6000/api/v1/pipelines`** while `./platform start` is running.

**Custom Docker pipelines:** see **`docs/VERITAS_PIPELINE_DOCKER_FLOW.md`** (build → push to your registry, e.g. `docker.io/phindagijimana321/…` → YAML `image` → job → user reports).

**Production:** **`docs/VERITAS_PRODUCTION.md`**, **`veritas/veritas_full_repo/backend/.env.production.example`**, Gunicorn **`Dockerfile`**, root **`GET /health`** / **`GET /ready`** for probes, optional **`TRUSTED_HOSTS`**. Frontend: set **`VITE_VERITAS_API_BASE_URL`** (e.g. `http://127.0.0.1:6000/api/v1`) and rebuild so the UI probes the API and lists live pipelines on the Pipeline page.

## Executable bit

If needed:

`chmod +x api platform atlas vt bin/api bin/platform bin/atlas bin/veritas scripts/dev-stack.sh scripts/full_local_run.sh scripts/full_local_e2e.py`
