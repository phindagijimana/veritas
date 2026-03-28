# Operations

## Health checks (Kubernetes / load balancers)

| Endpoint | Role |
|----------|------|
| **`GET /health`** | **Liveness** — process is up; always `200` if the app is running. |
| **`GET /ready`** | **Readiness** — database reachable; returns **`503`** if `SELECT 1` fails (do not send traffic). |

Uvicorn behind a reverse proxy: use **`--proxy-headers`** (and trusted proxies) so client IP and HTTPS are correct for logs and optional rate limits.

## Metrics

When `ATLAS_METRICS_ENABLED=true` (default), Prometheus metrics are exposed at **`GET /metrics`**. `/health`, `/ready`, and `/metrics` are excluded from request latency histograms.

## Logging

- **`ATLAS_LOG_LEVEL`** — default `INFO` (applies to the `atlas.*` logger namespace).
- **`ATLAS_LOG_JSON=true`** — one JSON object per line on stdout for `atlas.access` and other `atlas.*` loggers (uvicorn keeps its own format unless you configure it separately).

Access lines look like: `method=GET path=/api/v1/... status=200 request_id=... duration_ms=...`.

## Request correlation

Every response includes **`X-Request-ID`** (echoed from the incoming header or generated). Use it to tie access logs to upstream gateways and downstream services.

## CORS

Set **`ATLAS_CORS_ORIGINS`** to a comma-separated list of browser origins (e.g. `https://app.example.com,http://localhost:3000`). Leave empty to disable CORS middleware. In **`ATLAS_ENV=production`**, wildcard **`*`** is rejected.

## Rate limits

1. **Gateway (recommended for HA)** — Enforce per-IP or per-key limits at nginx, Envoy, or your cloud WAF for `/api/v1/admin/*` and public routes.
2. **Optional in-process** — Set **`ATLAS_ADMIN_RATE_LIMIT_PER_MINUTE`** to a positive integer to apply a **per-IP sliding window** (60s) on **`/api/v1/admin/*`) only. Uses in-memory state (fine for a single worker; use the gateway when running multiple replicas).

## Audit trail

Grant create/update/revoke and staging manifest outcomes write rows to **`atlas_audit_events`**.  
Query via **`GET /api/v1/admin/audit-events`** (admin auth).

## Secret rotation

1. **Internal API key:** rotate `ATLAS_INTERNAL_API_KEY`; update Veritas or automation clients; deploy; invalidate old key at the gateway if applicable.
2. **JWT / OIDC:** rotate keys at the identity provider; update `ATLAS_JWKS_URL` if the JWKS endpoint URL changes.
3. **Pennsieve:** rotate `PENNSIEVE_API_TOKEN` / secret in the secret store; restart Atlas API workers with zero-downtime if possible.
4. **Veritas client secret:** rotate `ATLAS_VERITAS_CLIENT_SECRET` on Atlas and the matching Veritas backend configuration together.

## Dependency pinning

- **pyproject.toml** specifies minimum compatible versions.
- **`requirements-lock.txt`** pins a known-good transitive set (regenerate in a clean virtualenv; see the file header). Typical install: `pip install -r requirements-lock.txt && pip install --no-deps -e .`
- Alternatives: **pip-tools** (`pip-compile`), **uv**, or **Poetry** lockfiles in CI.

## Database

Atlas expects **PostgreSQL** by default (`psycopg2-binary` is a core dependency). Local development: `docker compose up -d` in `atlas_api_app/` then `alembic upgrade head`.

## CI

See `.github/workflows/atlas-api-ci.yml`: tests and `alembic upgrade head` against PostgreSQL.
