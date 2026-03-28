# Veritas — production deployment

## Preconditions

1. **PostgreSQL** with database created; run **`alembic upgrade head`** before first boot.
2. **Redis** if `JOB_QUEUE_ENABLED=true` (Celery job monitor / sweeps).
3. **Secrets**: `AUTH_SECRET_KEY`, `ATLAS_API_CLIENT_SECRET` (match Atlas `ATLAS_VERITAS_CLIENT_SECRET`), DB password.
4. **Environment**: copy **`veritas/veritas_full_repo/backend/.env.production.example`** and set real values. `APP_ENV=production` enables **`validate_production_settings()`** (fails fast on unsafe defaults).

## API process

- **Development:** `uvicorn app.main:app --host 0.0.0.0 --port 6000`
- **Production:** **`gunicorn`** with **`uvicorn.workers.UvicornWorker`** (see `backend/Dockerfile`). Override worker count: **`WEB_CONCURRENCY`**.
- **Celery:** run **`./platform worker`** (or your process manager) with the **same** env as the API.

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

## Checklist

| Item | Done |
|------|------|
| `DEBUG=false`, `SEED_DEMO_DATA_ON_STARTUP=false` | |
| Real `DATABASE_URL`, migrations applied | |
| `AUTH_ENABLED=true` + strong `AUTH_SECRET_KEY` | |
| Real Atlas URL + secret if `ATLAS_INTEGRATION_MODE=live` | |
| `HPC_MODE=slurm` + `SSH_STRICT_HOST_KEY_CHECKING=true` if using SSH | |
| CORS origins = production UI URLs | |
| TLS termination (ingress / reverse proxy) | |
| Celery worker + Redis if async queue enabled | |
