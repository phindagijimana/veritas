# Veritas & Atlas Data API

Clinical AI validation stack: **Atlas** exposes dataset access, staging, and policy; **Veritas** runs biomarker pipeline evaluation, HPC/Slurm jobs, and reporting—with optional integration between the two.

| Component | Role | Default port |
|-----------|------|--------------|
| **Atlas Data API** | Datasets, staging, grants, Pennsieve-backed public data | `8000` |
| **Veritas Platform API** | Pipelines, jobs, HPC, MELD/IDEAS workflows, artifacts | `6000` |
| **Veritas UI** (optional) | Product frontend (Vite) | `7000` |

---

## Repository layout

| Path | Description |
|------|-------------|
| `atlas_api/atlas_api_app/` | Atlas Data API (FastAPI) |
| `veritas/veritas_full_repo/backend/` | Veritas API |
| `veritas/veritas_full_repo/frontend/` | Veritas web UI |
| `docs/` | Architecture and operations (MELD, production, pipelines) |
| `scripts/` | Dev stack, E2E helpers, MELD/IDEAS smoke tests |

---

## Quick start

### Atlas API

```bash
./api install          # or ./api venv && ./api install
cp atlas_api/atlas_api_app/.env.example atlas_api/atlas_api_app/.env
# Set database URL; run Postgres (see atlas_api_app README) then:
./api migrate
./api start            # http://127.0.0.1:8000
```

### Veritas Platform

```bash
./platform install
cp veritas/veritas_full_repo/backend/env.local.sqlite.example veritas/veritas_full_repo/backend/.env
./platform start       # http://127.0.0.1:6000 — GET /health
```

For PostgreSQL/Redis (production-like), use `veritas/veritas_full_repo/backend/docker-compose.yml`, copy `backend/.env.example` → `.env`, then `./platform migrate && ./platform start`.

### Veritas UI (local dev)

```bash
cp veritas/veritas_full_repo/frontend/env.local.example veritas/veritas_full_repo/frontend/.env.local
cd veritas/veritas_full_repo/frontend && npm install && npm run dev
```

`VITE_VERITAS_API_BASE_URL=/api/v1` uses the Vite dev proxy; ensure the Veritas API is running.

### IDEAS BIDS on your filesystem

Point Veritas at a local **BIDS root** (extracted IDEAS tree) so MELD/Slurm scripts can resolve subjects when no Atlas staging path is set:

```bash
# veritas/veritas_full_repo/backend/.env
MELD_IDEAS_DEFAULT_STAGING_PATH=/path/to/bids_IDEAS
```

For `scripts/meld_prepare_bids_input.py` and `./scripts/test_meld_ideas_smoke.sh`, set **`IDEAS_BIDS_ROOT`** to the same directory (or pass `--bids-root`). See [`docs/MELD_VERITAS_ATLAS.md`](docs/MELD_VERITAS_ATLAS.md).

---

## Atlas ↔ Veritas integration

Use the **same client secret** on both sides when Veritas calls Atlas (`ATLAS_INTEGRATION_MODE=live`):

| Atlas (`atlas_api_app/.env`) | Veritas (`backend/.env`) |
|------------------------------|---------------------------|
| `ATLAS_VERITAS_CLIENT_SECRET=<shared>` | `ATLAS_API_CLIENT_SECRET=<shared>` |
| — | `ATLAS_API_BASE_URL=http://127.0.0.1:8000/api/v1` |
| `ATLAS_PUBLIC_BASE_URL=http://127.0.0.1:8000` | — |

Full stack with Docker: `./scripts/dev-stack.sh up` (see script for Postgres ports). Run Alembic in each app after DBs are up.

---

## Operations & references

| Topic | Document |
|-------|----------|
| MELD Graph + IDEAS | [`docs/MELD_VERITAS_ATLAS.md`](docs/MELD_VERITAS_ATLAS.md) |
| Veritas production deploy | [`docs/VERITAS_PRODUCTION.md`](docs/VERITAS_PRODUCTION.md) |
| Custom pipeline images | [`docs/VERITAS_PIPELINE_DOCKER_FLOW.md`](docs/VERITAS_PIPELINE_DOCKER_FLOW.md) |
| IDEAS prepare smoke test | `./scripts/test_meld_ideas_smoke.sh` |

**MELD container (Podman “insufficient UIDs”):** see **Podman / rootless** in [`docs/MELD_VERITAS_ATLAS.md`](docs/MELD_VERITAS_ATLAS.md) — **`sudo ./scripts/fix_podman_rootless_subuid.sh`** then re-login, or **`./scripts/meld_run_apptainer.sh`** (Apptainer, no Docker).

**Health checks:** Veritas exposes `GET /health` and `GET /ready` (and under `/api/v1` where applicable).

**MELD / Slurm on Veritas:** set `RUNTIME_ENGINE=apptainer` or `singularity` and `MELD_IDEAS_DEFAULT_STAGING_PATH` in `backend/.env`. **Preview** generated scripts without submitting: `POST /api/v1/jobs/preview/{request_id}` with the same JSON body as job submit. **Inspect** stored sbatch: `GET /api/v1/jobs/{id}?include_script=1`.

---

## CLI entrypoints

| Script | Service |
|--------|---------|
| `./api` | Atlas API (`bin/api`) — `install`, `start`, `migrate`, `test`, `dev-token` |
| `./platform` | Veritas API (`bin/platform`) — `install`, `start`, `migrate`, `test`, `worker` |

Environment overrides: `ATLAS_HOST` / `ATLAS_PORT`, `VERITAS_HOST` / `VERITAS_PORT`.
