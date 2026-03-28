#!/usr/bin/env bash
# One-shot: Docker infra + migrations + instructions + optional E2E HTTP (requires Atlas & Veritas already running).
# For a true full run: run this, then start Atlas and Veritas in two terminals (see printed commands), then run E2E again or use --e2e-only.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$ROOT/bin:$PATH"

E2E_ONLY=false
for arg in "$@"; do
  if [[ "$arg" == "--e2e-only" ]]; then E2E_ONLY=true; fi
done

SECRET="${ATLAS_VERITAS_CLIENT_SECRET:-${ATLAS_API_CLIENT_SECRET:-dev-shared-atlas-veritas-secret}}"
export ATLAS_VERITAS_CLIENT_SECRET="$SECRET"
export ATLAS_API_CLIENT_SECRET="$SECRET"

if [[ "$E2E_ONLY" == true ]]; then
  exec python3 "$ROOT/scripts/full_local_e2e.py"
fi

echo "== Docker: Atlas + Veritas stacks =="
"$ROOT/scripts/dev-stack.sh" up

echo ""
echo "== Alembic: Atlas =="
(cd "$ROOT/atlas_api/atlas_api_app" && python3 -m alembic upgrade head)

echo ""
echo "== Alembic: Veritas =="
(cd "$ROOT/veritas/veritas_full_repo/backend" && python3 -m alembic upgrade head)

echo ""
echo "== Start APIs (two terminals, from repo root $ROOT) =="
echo "Terminal A — Atlas:"
echo "  cd $ROOT && export ATLAS_VERITAS_CLIENT_SECRET='$SECRET' && ./api start"
echo ""
echo "Terminal B — Veritas:"
echo "  cd $ROOT && export ATLAS_INTEGRATION_MODE=live ATLAS_API_BASE_URL=http://127.0.0.1:8000/api/v1 \\"
echo "    ATLAS_API_CLIENT_ID=veritas ATLAS_API_CLIENT_SECRET='$SECRET' && ./platform start"
echo ""
echo "Then in a third terminal:"
echo "  cd $ROOT"
echo "  export ATLAS_VERITAS_CLIENT_SECRET='$SECRET' ATLAS_API_CLIENT_SECRET='$SECRET'"
echo "  python3 scripts/full_local_e2e.py"
echo "  # or: ./scripts/full_local_run.sh --e2e-only"
echo ""
