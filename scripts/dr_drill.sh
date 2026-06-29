#!/usr/bin/env bash
# DR drill — exercise the backup → wipe → restore → verify path end-to-end.
#
# Runs entirely on whatever Postgres you point it at. Default mode creates
# a throwaway database, seeds synthetic state, takes a backup with
# backup_postgres.sh, drops the database, restores from the backup, and
# verifies row counts match.
#
# Usage:
#   dr_drill.sh --pg-host 127.0.0.1 --pg-port 5432 --pg-user veritas \
#               --pg-password veritas --work-dir /var/tmp/veritas-drill
#
# Or against a managed Postgres (no superuser):
#   dr_drill.sh --pg-host db.example --pg-user veritas --pg-password ... \
#               --db veritas_drill_$(date +%s)
#
# Exit codes:
#   0  drill succeeded (row counts match, backup file present, restore
#      reproducible)
#   2  CLI usage error
#   3  could not reach Postgres
#   4  backup_postgres.sh failed
#   5  drop/restore failed
#   6  verification mismatch (DATA LOSS in this drill — investigate)

set -euo pipefail

PG_HOST=127.0.0.1
PG_PORT=5432
PG_USER=veritas
PG_PASSWORD=""
DB="veritas_drill_$(date +%s)"
WORK_DIR="/var/tmp/veritas-drill"
ROWS_AUDIT=200
ROWS_REQUESTS=50
KEEP=false

usage() {
  cat <<USAGE
Usage: $0 [options]
  --pg-host HOST          (default 127.0.0.1)
  --pg-port PORT          (default 5432)
  --pg-user USER          (default veritas)
  --pg-password PASS      (or set PGPASSWORD env)
  --db NAME               (default veritas_drill_<timestamp>)
  --work-dir DIR          (default /var/tmp/veritas-drill)
  --rows-audit N          synthetic audit_events to seed (default 200)
  --rows-requests N       synthetic eval_requests to seed (default 50)
  --keep                  do not drop the drill database at the end
  -h, --help              show this

The drill writes a single dump file to <work-dir>/<db>.dump.gz and a log
file <work-dir>/<db>.log. Both are kept on failure for inspection.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pg-host) PG_HOST="$2"; shift 2 ;;
    --pg-port) PG_PORT="$2"; shift 2 ;;
    --pg-user) PG_USER="$2"; shift 2 ;;
    --pg-password) PG_PASSWORD="$2"; shift 2 ;;
    --db) DB="$2"; shift 2 ;;
    --work-dir) WORK_DIR="$2"; shift 2 ;;
    --rows-audit) ROWS_AUDIT="$2"; shift 2 ;;
    --rows-requests) ROWS_REQUESTS="$2"; shift 2 ;;
    --keep) KEEP=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -n "$PG_PASSWORD" ]]; then export PGPASSWORD="$PG_PASSWORD"; fi

mkdir -p "$WORK_DIR"
LOG="$WORK_DIR/$DB.log"
DUMP="$WORK_DIR/$DB.dump.gz"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() { printf '[dr-drill %s] %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$LOG"; }

trap 'log "FAILED at line $LINENO (exit=$?)"; exit ${EXIT_CODE:-1}' ERR

# ---------- 1. ping Postgres ----------------------------------------------
log "step 1: reach Postgres at $PG_HOST:$PG_PORT as $PG_USER"
EXIT_CODE=3
pg_isready -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" >/dev/null

# ---------- 2. create + seed drill database ------------------------------
EXIT_CODE=4
log "step 2: create database $DB and seed synthetic state"
psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$DB\";"

psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$DB" -v ON_ERROR_STOP=1 <<SQL
CREATE TABLE audit_events (
  id bigserial PRIMARY KEY,
  user_email text NOT NULL,
  action text NOT NULL,
  target_type text,
  target_id text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE eval_requests (
  id bigserial PRIMARY KEY,
  pipeline text NOT NULL,
  dataset text NOT NULL,
  state text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO audit_events (user_email, action, target_type, target_id)
SELECT
  'researcher' || (i % 5) || '@example.test',
  (ARRAY['login','submit','download','export','grant'])[1 + (i % 5)],
  'eval_request',
  i::text
FROM generate_series(1, $ROWS_AUDIT) AS i;

INSERT INTO eval_requests (pipeline, dataset, state)
SELECT
  'meld-graph-v2.2.4',
  'ideas-v1',
  (ARRAY['submitted','queued','running','completed','failed'])[1 + (i % 5)]
FROM generate_series(1, $ROWS_REQUESTS) AS i;
SQL

ROW_BEFORE_AUDIT=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$DB" -tAc "SELECT count(*) FROM audit_events;")
ROW_BEFORE_REQ=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$DB" -tAc "SELECT count(*) FROM eval_requests;")
log "  seeded: audit_events=$ROW_BEFORE_AUDIT  eval_requests=$ROW_BEFORE_REQ"

# ---------- 3. take backup with the shipped script ------------------------
EXIT_CODE=4
log "step 3: invoke backup_postgres.sh"
"$SCRIPT_DIR/backup_postgres.sh" \
    --db-url "postgresql://$PG_USER:${PG_PASSWORD:-$PGPASSWORD}@$PG_HOST:$PG_PORT/$DB" \
    --out-dir "$WORK_DIR" \
    --prefix "$DB" \
    --retention-days 1 >>"$LOG" 2>&1

LATEST_DUMP=$(ls -1t "$WORK_DIR/${DB}-"*.dump.gz 2>/dev/null | head -n1 || true)
if [[ -z "$LATEST_DUMP" || ! -s "$LATEST_DUMP" ]]; then
  log "  ERROR: backup_postgres.sh did not produce a non-empty dump"
  exit 4
fi
DUMP_BYTES=$(stat -c '%s' "$LATEST_DUMP")
log "  dump ok: $LATEST_DUMP ($DUMP_BYTES bytes)"

# ---------- 4. simulate disaster: drop + recreate empty -------------------
EXIT_CODE=5
log "step 4: simulate disaster — drop database $DB"
psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE \"$DB\";"
psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"$DB\";"

# ---------- 5. restore --------------------------------------------------------
log "step 5: restore from dump"
gunzip -c "$LATEST_DUMP" | pg_restore --no-owner --no-acl \
    -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$DB" >>"$LOG" 2>&1

# ---------- 6. verify ---------------------------------------------------------
EXIT_CODE=6
log "step 6: verify row counts"
ROW_AFTER_AUDIT=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$DB" -tAc "SELECT count(*) FROM audit_events;")
ROW_AFTER_REQ=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$DB" -tAc "SELECT count(*) FROM eval_requests;")
log "  restored: audit_events=$ROW_AFTER_AUDIT  eval_requests=$ROW_AFTER_REQ"

if [[ "$ROW_BEFORE_AUDIT" != "$ROW_AFTER_AUDIT" || "$ROW_BEFORE_REQ" != "$ROW_AFTER_REQ" ]]; then
  log "  MISMATCH — drill FAILED. Investigate $LOG and $LATEST_DUMP."
  exit 6
fi

# Spot-check a row to make sure data, not just counts, survived.
SAMPLE=$(psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$DB" -tAc \
  "SELECT user_email FROM audit_events WHERE id = 1;")
if [[ -z "$SAMPLE" ]]; then
  log "  row content check failed (audit_events.id=1 returned empty)"
  exit 6
fi
log "  content spot-check ok (audit_events.id=1.user_email=$SAMPLE)"

# ---------- 7. teardown -------------------------------------------------------
if [[ "$KEEP" == "false" ]]; then
  log "step 7: drop drill database $DB"
  psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d postgres -v ON_ERROR_STOP=1 -c "DROP DATABASE \"$DB\";"
fi

log "DR drill PASSED. RTO measurement: log timestamps in $LOG."
echo "OK"
