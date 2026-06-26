#!/usr/bin/env bash
# Nightly Postgres dump for Veritas / Atlas. Atomic write, gzip, retention prune.
#
# Usage:
#   backup_postgres.sh --db-url postgresql://... --out-dir /backups --retention-days 30
#   backup_postgres.sh --db-url file:///etc/veritas/db.url --out-dir /backups
#
# Exits non-zero on any failure so cron / a systemd OnFailure can alert.

set -euo pipefail

DB_URL=""
OUT_DIR=""
RETENTION_DAYS=30
PREFIX="veritas"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --db-url) DB_URL="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --retention-days) RETENTION_DAYS="$2"; shift 2 ;;
    --prefix) PREFIX="$2"; shift 2 ;;
    -h|--help)
      cat <<USAGE
Usage: $0 --db-url <URL> --out-dir <DIR> [--retention-days N] [--prefix NAME]

DB URL forms:
  postgresql://user:pass@host:5432/db   (used as-is)
  file:///path/to/url-file              (read URL from file, one line)

The dump is written as: <out-dir>/<prefix>-<host>-<UTC timestamp>.dump.gz
USAGE
      exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "$DB_URL" ]]; then DB_URL="${DATABASE_URL:-}"; fi
if [[ -z "$DB_URL" ]]; then echo "error: --db-url or DATABASE_URL required" >&2; exit 2; fi
if [[ -z "$OUT_DIR" ]]; then echo "error: --out-dir required" >&2; exit 2; fi

# Resolve file:// URL form.
if [[ "$DB_URL" =~ ^file:// ]]; then
  DB_URL="$(cat "${DB_URL#file://}")"
fi

# pg_dump accepts postgresql:// URIs since 9.2; pg_restore likewise. Strip any
# SQLAlchemy-specific +driver suffix (postgresql+psycopg://...).
DB_URL_PG="${DB_URL/postgresql+psycopg2:\/\//postgresql:\/\/}"
DB_URL_PG="${DB_URL_PG/postgresql+psycopg:\/\//postgresql:\/\/}"

mkdir -p "$OUT_DIR"
HOST="$(hostname -s)"
STAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
TARGET="${OUT_DIR}/${PREFIX}-${HOST}-${STAMP}.dump.gz"
TMP="${TARGET}.part"

trap 'rm -f "$TMP"' EXIT

# Pipe pg_dump → gzip → temp file. -F c = custom (compressed) format, gives
# us pg_restore --jobs parallelism on the way back.
PGPASSWORD="" pg_dump -F c --no-owner --no-privileges --dbname "$DB_URL_PG" \
  | gzip -9 > "$TMP"

# fsync + atomic rename so a crash mid-write never produces a half-file.
sync
mv -f "$TMP" "$TARGET"

SIZE="$(stat -c %s "$TARGET" 2>/dev/null || stat -f %z "$TARGET")"
echo "wrote $TARGET ($SIZE bytes)"

# Retention. find -mtime is whole-day granularity which is fine for nightly.
if [[ "$RETENTION_DAYS" -gt 0 ]]; then
  find "$OUT_DIR" -maxdepth 1 -type f -name "${PREFIX}-*.dump.gz" \
    -mtime +"$RETENTION_DAYS" -print -delete
fi

# Final sanity check: gzip integrity.
if ! gzip -t "$TARGET"; then
  echo "error: gzip integrity check failed for $TARGET" >&2
  exit 3
fi

echo "OK"
