# Veritas — production deployment

## Preconditions

1. **PostgreSQL** with database created; run **`alembic upgrade head`** before first boot.
2. **Redis** if `JOB_QUEUE_ENABLED=true` (Celery job monitor / sweeps).
3. **Secrets**: `AUTH_SECRET_KEY`, `ATLAS_API_CLIENT_SECRET` (match Atlas `ATLAS_VERITAS_CLIENT_SECRET`), DB password.
4. **Environment**: copy **`veritas/veritas_full_repo/backend/.env.production.example`** and set real values. `APP_ENV=production` enables **`validate_production_settings()`** (fails fast on unsafe defaults).

## API process

- **Development:** `uvicorn app.main:app --host 0.0.0.0 --port 6000` (same default as `./platform start` / `VERITAS_PORT`)
- **Production:** **`gunicorn`** with **`uvicorn.workers.UvicornWorker`** (see `backend/Dockerfile`). Override worker count: **`WEB_CONCURRENCY`**.
- **Celery:** run **`./platform worker`** (or your process manager) with the **same** env as the API.
- **Celery beat** (periodic job monitor sweep): `celery -A app.celery_app.celery_app beat`. Without beat, jobs only transition state when `POST /jobs/monitor/sweep` is called manually. Interval comes from `JOB_MONITOR_INTERVAL_SECONDS` (default 30s).

## HTTP / security

- **`GET /health`** — liveness (also **`GET /api/v1/health`**).
- **`GET /ready`** — readiness: DB, and Redis/S3 when configured (also **`GET /api/v1/ready`**).
- **`TRUSTED_HOSTS`** — optional comma-separated hostnames for `TrustedHostMiddleware` (use behind ingress).
- **CORS** — `ALLOWED_ORIGINS` must list explicit UI origins; **`*` is rejected** when `APP_ENV=production`.
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`; **HSTS** when `APP_ENV=production`.

## Frontend

- Build with **`VITE_VERITAS_API_BASE_URL`** pointing at your API (e.g. `https://api.veritas.example.com/api/v1`).
- See **`veritas/veritas_full_repo/frontend/.env.example`**.

## Docker

```bash
cd veritas/veritas_full_repo/backend
docker build -t veritas-api:latest .
docker run --env-file .env -p 6000:6000 veritas-api:latest
```

Health: `curl -fsS http://127.0.0.1:6000/health`

## First-admin bootstrap (production)

`POST /auth/register` always creates **researchers** (anti-escalation). The dev-user seed in `0014_users` only fires when `APP_ENV != production`, so a fresh production DB has **zero admins**. Bootstrap one with the CLI shipped in commit `0212c7b`:

```bash
# Inside the API container / pod (uses the API process's env)
veritas-api users create-admin --email you@example.org
# Generates a strong password if --password is omitted; prints it once.
# Idempotent: re-running on an existing user promotes them to admin instead of erroring.
```

Other CLI commands: `users set-password --email …`, `users set-role --email … --role admin|researcher`, `users list`.

Same workflow via API (after the first admin exists):
- `GET /admin/users` — list everyone
- `PATCH /admin/users/{email}/role` — promote / demote (refuses to demote the last active admin)
- `POST /admin/users/{email}/reset-password` — returns a one-time plaintext for OOB delivery

## API tokens (programmatic users)

Bearer JWTs expire after `AUTH_ACCESS_TOKEN_EXPIRE_MINUTES` (default 60). For CI / scripts use **PATs** instead:

- UI: **API tokens** nav item → create a labelled token, copy it once.
- API: `POST /auth/tokens` (must be JWT, not PAT — anti-pivot), `GET /auth/tokens`, `DELETE /auth/tokens/{id}`.
- Token format: `veritas_pat_<64 hex chars>`. Auth middleware recognizes either JWT or PAT in the same `Authorization: Bearer …` header.

## Audit log

Every write under `/api/v1/*` (POST/PUT/PATCH/DELETE) lands in the `audit_events` table via `AuditMiddleware`. Captures actor (email/role/jwt-or-pat), action name, subject (extracted from the URL when present), HTTP status, route, and IP. Reads (GETs) are deliberately not captured to keep volume manageable.

Admins view via **`GET /admin/audit`** with optional filters:
```bash
curl -H "Authorization: Bearer $JWT" \
  "https://api.veritas.example.com/api/v1/admin/audit?action=job.submit&limit=200"
curl -H "Authorization: Bearer $JWT" \
  "https://api.veritas.example.com/api/v1/admin/audit?actor_email=alice@example.org"
```

Default page size 100, max 500/request. Order: most-recent first.

## End-user feature surface (after Sprint C)

- **Login / register** (researchers only) and **JWT logout** — see `LoginGate.jsx`.
- **API tokens** page — create/list/revoke programmatic access tokens.
- **User Dashboard** — submit evaluation requests against Atlas datasets.
- **Veritas admin** (admins only) — connect HPC, preview/submit Slurm, view logs, download reports.
- **Leaderboard** — published, consented entries pulled from `GET /leaderboard` (no fake mock data).
- **Report downloads** — `GET /reports/{id}/download/{fmt}/file` streams pdf/json/csv/html with bearer auth. The UI fetches as a blob and triggers a save.
- **Job logs viewer** — `GET /jobs/{int_id}/logs?stream=stdout|stderr` returns the last 256 KB of the on-cluster log (text). UI panel pasted into the admin side panel.

## Checklist

| Item | Done |
|------|------|
| `DEBUG=false`, `SEED_DEMO_DATA_ON_STARTUP=false`, `DATABASE_AUTO_CREATE_SCHEMA=false` | |
| Real `DATABASE_URL` (Postgres, NOT SQLite), migrations applied via `alembic upgrade head` | |
| `AUTH_ENABLED=true` + strong `AUTH_SECRET_KEY` (≥32 bytes, e.g. `openssl rand -hex 32`) | |
| First admin bootstrapped via `veritas-api users create-admin` | |
| Real Atlas URL + secret if `ATLAS_INTEGRATION_MODE=live` | |
| `HPC_MODE=slurm` + `SSH_STRICT_HOST_KEY_CHECKING=true` if using SSH | |
| CORS origins = production UI URLs (`ALLOWED_ORIGINS` must NOT be `*`) | |
| TLS termination (ingress / reverse proxy) | |
| `TRUSTED_HOSTS` set if behind a reverse proxy | |
| Celery worker + Redis if `JOB_QUEUE_ENABLED=true` | |
| Celery beat running (so job state advances without manual sweep POST) | |
| Audit-log retention policy chosen (rotate `audit_events` at N days if write-heavy) | |
| Backups: nightly dump of Postgres + the artifact dir (`ARTIFACT_ROOT_DIR`) | |
| Monitoring: scrape `/metrics`, alert on `/ready` failures | |
