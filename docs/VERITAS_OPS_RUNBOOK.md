# Veritas — operations runbook

Day-to-day playbook for whoever owns the deployment. Companion to
[`VERITAS_PRODUCTION.md`](./VERITAS_PRODUCTION.md), which covers first-boot
configuration.

> Scope: PostgreSQL-backed deploy, gunicorn workers, optional Celery worker +
> beat, optional Atlas service, optional Slurm cluster. The dev SQLite path is
> not covered here — see the project root `README.md` for that.

---

## Identify the moving parts

| Component | Process | Default port | State on disk |
|-----------|---------|--------------|---------------|
| Veritas API | `gunicorn` + `uvicorn.workers.UvicornWorker` | 6000 | none |
| Postgres | system / managed service | 5432 | `$PGDATA` |
| Redis (optional) | `redis-server` | 6379 | `appendonly.aof` if persistence on |
| Celery worker (optional) | `celery -A app.celery_app.celery_app worker` | n/a | none |
| Celery beat (optional) | `celery -A app.celery_app.celery_app beat` | n/a | `celerybeat-schedule` |
| Atlas API (optional) | `uvicorn` | 8000 | none |
| Artifact root | flat directory on shared FS | n/a | `ARTIFACT_ROOT_DIR` |

Anything not durable enough to backup (Redis without persistence, Celery
worker queues) is recoverable by re-submitting — but the API DB and the
artifact dir hold all clinical evaluations and reports, so **those two are
the backup priority**.

---

## Backups

### Postgres dump (nightly)

```bash
# scripts/backup_postgres.sh — committed alongside this doc
./scripts/backup_postgres.sh \
  --db-url "$DATABASE_URL" \
  --out-dir /mnt/veritas-backups/pg \
  --retention-days 30
```

Behaviour:
- `pg_dump` in `custom` format (`-F c`), gzip-compressed inline.
- Filename: `veritas-<host>-<timestamp>.dump.gz`.
- Atomic write: dump to `*.part`, fsync, rename on success.
- Deletes anything in `--out-dir` older than `--retention-days`.
- Exits non-zero on any failure (cron should alert).

Cron line (UTC):
```cron
17 2 * * * /opt/veritas/scripts/backup_postgres.sh --db-url file:///etc/veritas/db.url --out-dir /mnt/veritas-backups/pg --retention-days 30 >> /var/log/veritas-backup.log 2>&1
```

If you can't store the URL in a file, set `DATABASE_URL` in the cron user's
environment and omit `--db-url`.

### Artifact directory (rsync)

Reports, sbatch scripts, run manifests live under `ARTIFACT_ROOT_DIR`
(default `./var/veritas_artifacts`). The DB references them by path — restore
is incomplete without them.

```bash
rsync -a --delete --link-dest=/mnt/veritas-backups/artifacts/prev \
  "$ARTIFACT_ROOT_DIR"/  /mnt/veritas-backups/artifacts/current/
mv /mnt/veritas-backups/artifacts/prev /mnt/veritas-backups/artifacts/old
mv /mnt/veritas-backups/artifacts/current /mnt/veritas-backups/artifacts/prev
```

That gives you hardlinked daily snapshots cheap on disk. Keep the same
retention as Postgres; align timestamps so a paired restore is unambiguous.

### Off-site copies

Both targets above are local. Replicate `/mnt/veritas-backups` to off-site
storage (S3 / GCS / a different rack) at least daily; use bucket versioning
or a write-once policy if the audit log lives in scope of a compliance
regime that requires retention guarantees.

---

## Restore

> Practice this on a staging box before you need it. The first time is
> always slower than you think.

### Postgres

```bash
# 1. Stop the API + Celery so nothing writes during restore.
systemctl stop veritas-api veritas-celery veritas-celery-beat

# 2. Drop and recreate the schema (or restore into a fresh DB).
psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# 3. Load the dump.
gunzip -c /mnt/veritas-backups/pg/veritas-prod-2026-06-10T02-17Z.dump.gz \
  | pg_restore --no-owner --no-privileges --dbname "$DATABASE_URL"

# 4. Bring the schema up to head (in case the snapshot pre-dates the running code).
cd backend && DATABASE_URL=$DATABASE_URL APP_ENV=production python3 -m alembic upgrade head

# 5. Confirm and restart.
psql "$DATABASE_URL" -c "SELECT version_num FROM alembic_version;"
systemctl start veritas-api veritas-celery veritas-celery-beat
curl -fsS https://api.veritas.example.com/ready
```

### Artifact directory

```bash
rsync -a /mnt/veritas-backups/artifacts/prev/ "$ARTIFACT_ROOT_DIR"/
```

Spot-check that a recent report's `pdf_path` still resolves:
```bash
psql "$DATABASE_URL" -c "SELECT pdf_path FROM reports ORDER BY id DESC LIMIT 1;" \
  | grep -oE '/[^[:space:]]+' | xargs -I{} test -f {} && echo OK
```

### Verification checklist after restore

- [ ] `GET /ready` returns 200 with `database: ok`.
- [ ] An admin can sign in (passwords use bcrypt and are deterministic across restore).
- [ ] The leaderboard renders past entries.
- [ ] A known report's `Download PDF` button still works (file path is real).
- [ ] Audit log shows the restore-time gap; document the incident in there
      via a one-off CLI insert if you want a permanent marker.

---

## Schema upgrades

### Forward (normal release)

```bash
# 0. Tag the release for rollback.
git tag prod-2026-06-10 && git push --tags

# 1. Snapshot the DB FIRST. Even for "trivial" migrations.
./scripts/backup_postgres.sh --db-url "$DATABASE_URL" --out-dir /tmp/preupgrade

# 2. Pull, build, run migrations against the live DB.
git pull
docker build -t veritas-api:$(git rev-parse --short HEAD) backend
DATABASE_URL=$DATABASE_URL APP_ENV=production python3 -m alembic upgrade head

# 3. Rolling restart of API workers (gunicorn SIGHUP) and the Celery worker.
systemctl reload veritas-api
systemctl restart veritas-celery
```

The Atlas-side migration uses an independent Alembic tree
(`atlas_api/atlas_api_app/alembic/`). Run separately with `ATLAS_DATABASE_URL`.

### Rollback (something broke)

Alembic rollbacks are **not** sufficient if the new code uses a column that
the old code doesn't write — old workers will crash on `INSERT … RETURNING`
mismatches. The safe drill is:

```bash
# 1. Restore the pre-upgrade dump (see above).
gunzip -c /tmp/preupgrade/veritas-*.dump.gz | pg_restore --clean --dbname "$DATABASE_URL"

# 2. Roll the code back.
git checkout prod-2026-06-10

# 3. Re-deploy the old image.
docker build -t veritas-api:rollback backend
systemctl restart veritas-api veritas-celery
```

`alembic downgrade -1` only makes sense for schema changes that are purely
additive and unused by the new code path (rare).

---

## Scheduled tasks

| Task | Cadence | Owner |
|------|---------|-------|
| Postgres backup | nightly 02:17 UTC | systemd timer / cron |
| Artifact rsync | nightly 03:00 UTC | systemd timer / cron |
| Off-site sync | nightly 04:00 UTC | systemd timer / cron |
| Celery beat (`run_job_monitor_sweep`) | every `JOB_MONITOR_INTERVAL_SECONDS` (default 30 s) | the beat process itself |
| Audit-log archive + prune | monthly 03:30 UTC on the 1st | `scripts/audit_retention.sh` (see below) |
| TLS cert renewal | depends on issuer | certbot / ACME client |

### Audit-log retention (cron + systemd)

`audit_events` accumulates one row per state-changing write. For most
deployments the table grows by ~5-20k rows / day; nine months of that fits
in a few hundred MB on Postgres. If you want to cap it, the shipped script
archives + deletes rows older than `--days N` in a single safe pass: it
writes a gzipped CSV first, verifies the gzip, *then* deletes — so a crash
mid-script can't lose rows that weren't archived.

```cron
30 3 1 * * /opt/veritas/scripts/audit_retention.sh \
  --db-url file:///etc/veritas/db.url \
  --archive-dir /mnt/veritas-backups/audit \
  --days 365 \
  >> /var/log/veritas-audit-retention.log 2>&1
```

Or via systemd:

```ini
# /etc/systemd/system/veritas-audit-retention.service
[Unit]
Description=Veritas audit_events archive + prune

[Service]
Type=oneshot
User=veritas
EnvironmentFile=/etc/veritas/db.env
ExecStart=/opt/veritas/scripts/audit_retention.sh \
  --db-url ${DATABASE_URL} \
  --archive-dir /mnt/veritas-backups/audit \
  --days 365

# /etc/systemd/system/veritas-audit-retention.timer
[Unit]
Description=Run audit_events retention monthly

[Timer]
OnCalendar=*-*-01 03:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

The script is idempotent — running it twice in the same hour archives
zero rows the second time. Each run prints a line you can grep:

```
found 142318 audit_events older than 365 days; archiving …
archived: 142318 rows → /mnt/veritas-backups/audit/veritas-audit-archive-2027-06-01T03-30-15Z-365d.csv.gz (8927204 bytes)
deleted:  142318 rows
OK
```

---

## Incident triage

### "API is down"

1. `curl -fsS https://api.veritas.example.com/health` — liveness.
2. `curl -fsS https://api.veritas.example.com/ready` — readiness; if 503, check the body for which dependency.
3. `journalctl -u veritas-api -n 200 --no-pager` — last logs.
4. If gunicorn workers are healthy but DB is down, the API itself is fine; restoring DB fixes it.
5. If gunicorn workers keep crashing on import, that's a code or env regression — `git log` the last release tag.

### "Jobs aren't progressing"

1. `GET /jobs/<id>` — what's the current `status`?
2. Audit log: `GET /admin/audit?action=job.advance&subject_id=<job_id>` — when did it last transition?
3. Is the beat process running? `systemctl status veritas-celery-beat`. Without beat, jobs only progress when `POST /jobs/monitor/sweep` is called.
4. Is `HPC_MODE=slurm` and the SSH cluster reachable? `GET /hpc/summary` shows the active connection.

### "Reports aren't being delivered to users"

1. Was the notification written? `GET /notifications` as the affected user, or `psql -c "SELECT … FROM notifications WHERE user_email='alice@…' ORDER BY id DESC LIMIT 5;"`.
2. Bell badge missing despite row in DB → frontend issue, check `/api/v1/notifications` response in browser devtools.
3. Email missing → `EMAIL_ENABLED` set? SMTP host reachable from the API container? `journalctl … | grep -i "email send to"` — failed sends log at `WARNING`.

### "A user can't sign in"

1. Check `/auth/mode` — confirm `AUTH_ENABLED=true`.
2. `veritas-api users list` — does the account exist? Is `is_active=true`?
3. If they forgot their password: `veritas-api users set-password --email …` (TTY prompts, autogenerates if you hit Enter).
4. If their PAT is leaked: revoke from UI (`/tokens`) or `DELETE /auth/tokens/<id>`.

### "Audit log is growing too fast"

Check the actual row count:
```sql
SELECT count(*), min(created_at), max(created_at) FROM audit_events;
```

If that's GBs per month, either:
- Trim retention (see the monthly archive task above).
- Tighten `AuditMiddleware` to skip very-noisy endpoints (rare, since reads aren't already captured).

---

## Operational invariants

The following must remain true. If you change one, audit how it interacts
with the others before deploying:

- **Migrations are run before code that depends on them.** `alembic upgrade
  head` happens during the deploy step that precedes the worker / API
  restart. Code that requires a new column won't even import cleanly.
- **The first active admin can't be demoted.** Endpoint refuses; the CLI
  refuses; the only way around is direct SQL — and you'll lose the audit
  trail of who did it.
- **PATs can't mint PATs.** `POST /auth/tokens` requires a JWT, not a PAT.
- **Audit log is append-only at the application layer.** No endpoint deletes
  rows. If you need retention, archive-and-delete via `psql` directly.
- **`/auth/register` produces only researchers.** Role escalation must go
  through `/admin/users/{email}/role`, which is audit-logged.

---

## Quick reference: where to look

| Thing | Place |
|-------|-------|
| Code | `veritas/veritas_full_repo/backend/app/` |
| Migrations | `veritas/veritas_full_repo/backend/alembic/versions/` |
| Frontend | `veritas/veritas_full_repo/frontend/src/` |
| Atlas | `atlas_api/atlas_api_app/` |
| Production config keys | `app/core/config.py` (`Settings` dataclass) |
| Deploy guide | `docs/VERITAS_PRODUCTION.md` |
| CI workflow | `.github/workflows/veritas-atlas-integration.yml` |
| Helper scripts | `scripts/` |
| Grafana dashboard JSON | `docs/grafana/veritas-overview.json` |
| Load-test scenario | `scripts/loadtest_veritas.py` |
