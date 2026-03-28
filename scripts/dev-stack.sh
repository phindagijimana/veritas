#!/usr/bin/env bash
# Bring up local Postgres/Redis/MinIO for both Atlas and Veritas (separate compose projects to avoid name clashes).
# Run from anywhere; paths are relative to this script's repo root.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ATLAS_COMPOSE="$ROOT/atlas_api/atlas_api_app/docker-compose.yml"
VERITAS_COMPOSE="$ROOT/veritas/veritas_full_repo/backend/docker-compose.yml"

usage() {
  cat <<'EOF'
Usage: scripts/dev-stack.sh {up|down|ps}

  up    Start Atlas stack (project atlas-dev) and Veritas stack (project veritas-dev)
  down  Stop both stacks
  ps    docker compose ps for both

Atlas:    Postgres 5432, Redis 6379, MinIO 9000 (API) / 9001 (console)
Veritas:  Postgres 5433, Redis 6380, MinIO 9002 / 9003

Then configure apps (see validator README “Local Atlas + Veritas”).
EOF
}

check_subuid_for_rootless() {
  # Only when the docker CLI is Podman (not Docker Engine). Real docker-ce does not need this.
  local bin
  bin="$(command -v docker 2>/dev/null || true)"
  if [[ -z "$bin" ]]; then
    return 0
  fi
  if [[ "$(basename "$(readlink -f "$bin" 2>/dev/null || echo "$bin")")" != "podman" ]]; then
    return 0
  fi
  local u
  u="$(id -un)"
  if [[ -r /etc/subuid ]] && ! grep -q "^${u}:" /etc/subuid 2>/dev/null; then
    echo "ERROR: No /etc/subuid entry for '${u}'. Rootless Podman cannot extract image layers." >&2
    echo "Run once (requires sudo): sudo $ROOT/scripts/fix_podman_rootless_subuid.sh" >&2
    echo "Then log out and back in, or open a new login session." >&2
    exit 1
  fi
}

cmd="${1:-}"
case "$cmd" in
  up)
    check_subuid_for_rootless
    docker compose -f "$ATLAS_COMPOSE" -p atlas-dev up -d
    docker compose -f "$VERITAS_COMPOSE" -p veritas-dev up -d
    echo ""
    echo "Started. Apply migrations:"
    echo "  (cd atlas_api/atlas_api_app && python -m alembic upgrade head)"
    echo "  (cd veritas/veritas_full_repo/backend && python -m alembic upgrade head)"
    ;;
  down)
    docker compose -f "$ATLAS_COMPOSE" -p atlas-dev down
    docker compose -f "$VERITAS_COMPOSE" -p veritas-dev down
    ;;
  ps)
    docker compose -f "$ATLAS_COMPOSE" -p atlas-dev ps
    docker compose -f "$VERITAS_COMPOSE" -p veritas-dev ps
    ;;
  ""|-h|--help|help)
    usage
    ;;
  *)
    echo "Unknown command: $cmd" >&2
    usage >&2
    exit 1
    ;;
esac
