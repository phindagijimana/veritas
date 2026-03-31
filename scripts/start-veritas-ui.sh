#!/usr/bin/env bash
# Veritas frontend (Vite) on port 7000 — API should be on 6000 (./platform start).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FE="$ROOT/veritas/veritas_full_repo/frontend"
if [[ ! -f "$FE/.env.local" ]]; then
  if [[ -f "$FE/env.local.example" ]]; then
    cp "$FE/env.local.example" "$FE/.env.local"
    echo "Created $FE/.env.local from env.local.example"
  fi
fi
cd "$FE"
if [[ ! -d node_modules ]]; then
  npm install
fi
exec npm run dev
