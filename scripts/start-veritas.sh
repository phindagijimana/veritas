#!/usr/bin/env bash
# Start Veritas API after clone (creates backend/.env from SQLite template if missing).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BE="$ROOT/veritas/veritas_full_repo/backend"
if [[ ! -f "$BE/.env" ]]; then
  cp "$BE/env.local.sqlite.example" "$BE/.env"
  echo "Created $BE/.env from env.local.sqlite.example"
fi
exec "$ROOT/platform" start "$@"
