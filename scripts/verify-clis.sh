#!/usr/bin/env bash
# Smoke-test ./platform and ./api wrappers (help + delegate to app CLI). Run from repo root: scripts/verify-clis.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

run() {
  echo "+ $*"
  "$@"
}

run ./platform --help >/dev/null
run ./api --help >/dev/null
run ./platform start --help >/dev/null
run ./api start --help >/dev/null
echo "OK: ./platform and ./api entrypoints work."
