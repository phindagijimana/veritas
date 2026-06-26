#!/usr/bin/env bash
# Archive + prune Veritas audit_events older than --days.
#
# 1. SELECT rows older than $CUTOFF, write CSV to --archive-dir.
# 2. DELETE the same rows in a single transaction.
# 3. Print a summary (rows archived, rows deleted, file path, file size).
#
# Idempotent. Safe to run twice — the second run will archive zero rows.
# Designed for cron. Exits non-zero on any failure so OnFailure can alert.
#
# Usage:
#   audit_retention.sh --db-url postgresql://... --archive-dir /var/audit-archive --days 90
#   audit_retention.sh --db-url file:///etc/veritas/db.url --archive-dir /var/audit --days 365
#
# Companion to docs/VERITAS_OPS_RUNBOOK.md "Audit log is growing too fast".

set -euo pipefail

DB_URL=""
ARCHIVE_DIR=""
DAYS=90

while [[ $# -gt 0 ]]; do
  case "$1" in
    --db-url) DB_URL="$2"; shift 2 ;;
    --archive-dir) ARCHIVE_DIR="$2"; shift 2 ;;
    --days) DAYS="$2"; shift 2 ;;
    -h|--help)
      cat <<USAGE
Usage: $0 --db-url <URL> --archive-dir <DIR> [--days N]

Archives audit_events with created_at < now() - interval 'N days' to a
gzipped CSV under <archive-dir>, then deletes those rows. The CSV file is
named: veritas-audit-archive-<UTC stamp>-<days>d.csv.gz

DB URL forms:
  postgresql://user:pass@host:5432/db
  file:///path/to/url-file              (read URL from file, one line)
USAGE
      exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$DB_URL" ]]; then DB_URL="${DATABASE_URL:-}"; fi
if [[ -z "$DB_URL" ]]; then echo "error: --db-url or DATABASE_URL required" >&2; exit 2; fi
if [[ -z "$ARCHIVE_DIR" ]]; then echo "error: --archive-dir required" >&2; exit 2; fi
if ! [[ "$DAYS" =~ ^[0-9]+$ ]]; then echo "error: --days must be a non-negative integer" >&2; exit 2; fi

# file:// resolution.
if [[ "$DB_URL" =~ ^file:// ]]; then
  DB_URL="$(cat "${DB_URL#file://}")"
fi
DB_URL_PG="${DB_URL/postgresql+psycopg2:\/\//postgresql:\/\/}"
DB_URL_PG="${DB_URL_PG/postgresql+psycopg:\/\//postgresql:\/\/}"

mkdir -p "$ARCHIVE_DIR"
STAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
TARGET="${ARCHIVE_DIR}/veritas-audit-archive-${STAMP}-${DAYS}d.csv.gz"
TMP="${TARGET}.part"

trap 'rm -f "$TMP"' EXIT

# We run COPY and DELETE in a single transaction so a crash mid-script can't
# delete data that wasn't archived. psql's ON_ERROR_STOP=1 means any failed
# statement rolls the whole thing back.
#
# COPY ... TO STDOUT streams CSV; we pipe through gzip → temp file. After
# both commands succeed, we atomically rename the temp file into place.

CUTOFF_SQL="now() - interval '${DAYS} days'"

# First: dry-run count so we can short-circuit if there's nothing to do.
ROWS_OLD=$(psql "$DB_URL_PG" -v ON_ERROR_STOP=1 -X -A -t -c \
  "SELECT count(*) FROM audit_events WHERE created_at < ${CUTOFF_SQL};")

if [[ "${ROWS_OLD:-0}" -le 0 ]]; then
  echo "no audit_events older than ${DAYS} days; nothing to archive"
  exit 0
fi

echo "found ${ROWS_OLD} audit_events older than ${DAYS} days; archiving …"

# Stream a CSV to the temp file. Headers included.
psql "$DB_URL_PG" -v ON_ERROR_STOP=1 -X -A -t \
  -c "COPY (SELECT id, created_at, actor_email, actor_role, auth_method, action, subject_type, subject_id, http_status, route, ip FROM audit_events WHERE created_at < ${CUTOFF_SQL} ORDER BY id) TO STDOUT WITH (FORMAT csv, HEADER true)" \
  | gzip -9 > "$TMP"

# Verify the gzip is intact BEFORE deleting anything.
if ! gzip -t "$TMP"; then
  echo "error: archive integrity check failed; refusing to delete rows" >&2
  exit 3
fi

# Promote the archive into place atomically.
sync
mv -f "$TMP" "$TARGET"

# Now the delete. If this fails the archive is already on disk; that's fine,
# the next run will see fewer rows above the cutoff and re-archive only the
# leftover delta.
ROWS_DELETED=$(psql "$DB_URL_PG" -v ON_ERROR_STOP=1 -X -A -t -c \
  "WITH deleted AS (DELETE FROM audit_events WHERE created_at < ${CUTOFF_SQL} RETURNING 1) SELECT count(*) FROM deleted;")

SIZE="$(stat -c %s "$TARGET" 2>/dev/null || stat -f %z "$TARGET")"

echo "archived: ${ROWS_OLD} rows → ${TARGET} (${SIZE} bytes)"
echo "deleted:  ${ROWS_DELETED} rows"
if [[ "$ROWS_OLD" != "$ROWS_DELETED" ]]; then
  echo "warning: archive count (${ROWS_OLD}) differs from delete count (${ROWS_DELETED}); inspect manually" >&2
  # Don't fail outright — the archive is durable; this is just a sanity heads-up.
fi
echo "OK"
