# Security policy

## Supported versions

| Version | Status        | Notes                                |
|---------|---------------|--------------------------------------|
| 0.1.x   | active        | Initial public release; patches land on `main` |
| < 0.1.0 | unsupported   | Pre-release; do not run in production |

Until `1.0.0` we treat any `0.x.y → 0.x.(y+1)` release as a fix bundle
that may include backwards-incompatible config changes; read the
release notes before upgrading a production deployment.

## Reporting a vulnerability

**Please do not file a public GitHub issue for security reports.**

Email **philbert_ndagijimana@urmc.rochester.edu** with:

1. A description of the vulnerability and the affected component
   (Veritas API, Veritas UI, Atlas API, deploy scripts).
2. The smallest reproducer you can produce (HTTP request, sample
   payload, screenshot — whatever's available).
3. Your assessment of impact (data exposure, RCE, privilege escalation,
   denial-of-service, audit-log tampering).
4. Whether the report is under any embargo on your end.

You should expect:

- An acknowledgement within **5 business days**.
- A triage decision and severity rating within **15 business days**.
- A coordinated-disclosure timeline if the issue is confirmed,
  typically **90 days** from acknowledgement to fix-and-release.
- Public credit in the release notes if you want it (and we agree the
  report was valid).

## Scope

In scope:

- The Veritas API (`backend/`), the Veritas UI (`veritas/veritas-ui/`),
  the Atlas API (`atlas_api/atlas_api_app/`), and the deploy scripts
  under `scripts/`.
- Default configurations shipped in `.env.production.example`.

Out of scope:

- Vulnerabilities that require an attacker who is already an
  authenticated admin (these are policy decisions, not bugs).
- Vulnerabilities in the underlying Slurm cluster, FreeSurfer license
  handling at the OS level, or third-party container images (report
  those upstream).
- Denial-of-service through brute-force HTTP — Veritas rate-limits at
  the application layer, but a full DoS posture is the operator's
  responsibility.
- Issues that only reproduce in `APP_ENV=development` with placeholder
  secrets (see `app/core/config.py: validate_production_settings`).

## Hardening checklist for operators

Production deployments must (enforced at boot by
`validate_production_settings`):

- Set `APP_ENV=production`, `DEBUG=false`, and a strong
  `AUTH_SECRET_KEY` (no placeholders).
- Use Postgres (not SQLite) and run `alembic upgrade head` before boot.
- Set `DATABASE_AUTO_CREATE_SCHEMA=false` and
  `SEED_DEMO_DATA_ON_STARTUP=false`.
- Set `SSH_STRICT_HOST_KEY_CHECKING=true` (or use a known-hosts
  jump-host).
- Replace `ATLAS_API_CLIENT_SECRET` with a real credential.
- Set `ALLOWED_ORIGINS` to explicit HTTPS origins (no `*`).
- Front the API with TLS at the load balancer or reverse proxy.
- Run the audit-log retention script
  (`scripts/audit_retention.sh`) on cron.
- Run the Postgres backup script
  (`scripts/backup_postgres.sh`) on cron.

The runtime threat model lives in `docs/threat-model.md`.
