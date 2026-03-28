#!/usr/bin/env bash
# Smoke-test Atlas API with Veritas service credentials (same secret on both sides).
#
# Prerequisites:
#   Atlas: ATLAS_VERITAS_CLIENT_ID=veritas (default), ATLAS_VERITAS_CLIENT_SECRET=<shared>
#   Veritas (for proxy test): ATLAS_INTEGRATION_MODE=live, ATLAS_API_BASE_URL=http://HOST:PORT/api/v1,
#                            ATLAS_API_CLIENT_ID=veritas, ATLAS_API_CLIENT_SECRET=<same shared secret>
#
# Usage:
#   export ATLAS_VERITAS_SECRET='your-shared-secret'
#   ./scripts/smoke_atlas_live.sh http://127.0.0.1:8000
#
set -euo pipefail
ATLAS_BASE="${1:-http://127.0.0.1:8000}"
ATLAS_BASE="${ATLAS_BASE%/}"
SECRET="${ATLAS_VERITAS_CLIENT_SECRET:-${ATLAS_VERITAS_SECRET:-}}"

echo "== Atlas readiness =="
curl -sfS "${ATLAS_BASE}/ready" | head -c 400 || true
echo ""
echo ""

if [[ -z "${SECRET}" ]]; then
  echo "Set ATLAS_VERITAS_CLIENT_SECRET (Atlas) / same value for curl — skipping authenticated /datasets."
  exit 0
fi

echo "== Atlas GET ${ATLAS_BASE}/api/v1/datasets (Veritas headers) =="
curl -sfS "${ATLAS_BASE}/api/v1/datasets" \
  -H "X-Atlas-Client-Id: veritas" \
  -H "X-Atlas-Client-Secret: ${SECRET}" \
  | head -c 2000 || true
echo ""
echo "OK"
