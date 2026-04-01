#!/usr/bin/env bash
# Full chain: Veritas/Atlas E2E (staging) → optional MELD Graph container verify.
#
# Prerequisites:
#   - Atlas + Veritas running with matching secrets (see scripts/full_local_e2e.py).
#   - Docker (for MELD steps).
#   - Licenses at validator repo root (same names as upstream Docker docs):
#       license.txt          — FreeSurfer
#       meld_license.txt     — MELD Graph
#   - MELD pytest: uses scripts/meld-compose.validator.yml (no meld_graph clone required).
#     Optional MELD_GRAPH_DIR= path to extracted meld_graph (compose.yml): licenses are
#     symlinked from this repo into that tree and upstream compose is used instead.
#
# Usage:
#   export ATLAS_API_CLIENT_SECRET=...   # same as Atlas ATLAS_VERITAS_CLIENT_SECRET
#   ./scripts/meld_veritas_full_run.sh
#
# Environment:
#   RUN_E2E=0          Skip full_local_e2e.py (use existing .veritas_last_e2e.json)
#   MELD_GRAPH_DIR=    Optional: extracted meld_graph with compose.yml (else use validator compose)
#   MELD_VERIFY=1      Run pytest in MELD container when licenses are present
#   MELD_VERIFY_STRICT=1  Exit with error if licenses missing but MELD_VERIFY=1
#   MELD_PULL=1        docker pull phindagijimana321/meld_graph:v2.2.4-nir2 before verify
#
# References:
#   - https://github.com/MELDProject/meld_graph
#   - https://meld-graph.readthedocs.io/en/latest/install_docker.html
#   - Model download issues: https://github.com/MELDProject/meld_graph/issues/102

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

ARTIFACT="$ROOT/.veritas_last_e2e.json"
MELD_COMPOSE="$ROOT/scripts/meld-compose.validator.yml"
RUN_E2E="${RUN_E2E:-1}"
MELD_VERIFY="${MELD_VERIFY:-1}"
MELD_PULL="${MELD_PULL:-0}"
MELD_VERIFY_STRICT="${MELD_VERIFY_STRICT:-0}"
export VALIDATOR_ROOT="$ROOT"

echo "== MELD + Veritas full run (repo: $ROOT) =="

if [[ "$RUN_E2E" != "0" ]]; then
  echo ""
  echo "Step 1: Atlas + Veritas E2E (writes $ARTIFACT) ..."
  python3 "$SCRIPT_DIR/full_local_e2e.py"
else
  echo ""
  echo "Step 1: Skipped (RUN_E2E=0); using existing artifact."
  if [[ ! -f "$ARTIFACT" ]]; then
    echo "ERROR: $ARTIFACT missing. Run with RUN_E2E=1 or copy artifact from a prior E2E run." >&2
    exit 1
  fi
fi

STAGED_PATH="$(python3 -c "
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
d = json.loads(p.read_text(encoding='utf-8'))
plan = (d.get('staging') or {}).get('plan') or {}
print(plan.get('staged_dataset_path') or '')
" "$ARTIFACT")"

echo ""
echo "Step 2: Staged dataset path (from Veritas plan):"
if [[ -n "$STAGED_PATH" ]]; then
  echo "  $STAGED_PATH"
  if [[ -d "$STAGED_PATH" ]]; then
    echo "  (directory exists on this host)"
  else
    echo "  (path not found locally — expected if staging is on another node or NFS layout differs)"
  fi
else
  echo "  (empty — check staging response in $ARTIFACT)"
fi

echo ""
echo "Step 3: MELD Graph (optional)"
echo "  MELD does not use Veritas generic --input/--output; follow upstream prepare_data +"
echo "  new_patient_pipeline after placing BIDS-ready data under meld_data/input (see docs/MELD_VERITAS_ATLAS.md)."

_fs_lic="$ROOT/license.txt"
_meld_lic="$ROOT/meld_license.txt"
_lic_ok=1
if [[ "$MELD_VERIFY" == "1" ]]; then
  if [[ ! -f "$_fs_lic" ]]; then
    echo ""
    echo "  FreeSurfer license not found: $_fs_lic"
    _lic_ok=0
  fi
  if [[ ! -f "$_meld_lic" ]]; then
    echo ""
    echo "  MELD license not found: $_meld_lic"
    _lic_ok=0
  fi
fi

if [[ "$MELD_VERIFY" == "1" ]]; then
  if [[ "$_lic_ok" != "1" ]]; then
    echo ""
    if [[ "$MELD_VERIFY_STRICT" == "1" ]]; then
      echo "ERROR: MELD_VERIFY_STRICT=1 but license file(s) missing (see messages above)." >&2
      exit 1
    fi
    echo "  Skipping MELD pytest (add license.txt and meld_license.txt under $ROOT)."
  else
    mkdir -p "$ROOT/meld_docker_data"
    if [[ "$MELD_PULL" == "1" ]]; then
      echo ""
      echo "Pulling phindagijimana321/meld_graph:v2.2.4-nir2 ..."
      docker pull phindagijimana321/meld_graph:v2.2.4-nir2
    fi
    export DOCKER_USER="${DOCKER_USER:-$(id -u):$(id -g)}"
    if [[ -n "${MELD_GRAPH_DIR:-}" ]]; then
      echo ""
      echo "Linking licenses into MELD_GRAPH_DIR=$MELD_GRAPH_DIR (upstream compose.yml) ..."
      ln -sf "$_fs_lic" "$MELD_GRAPH_DIR/license.txt"
      ln -sf "$_meld_lic" "$MELD_GRAPH_DIR/meld_license.txt"
      echo "Running MELD pytest ..."
      (cd "$MELD_GRAPH_DIR" && docker compose run meld_graph pytest)
    else
      echo ""
      echo "Running MELD pytest (compose: $MELD_COMPOSE) ..."
      (cd "$ROOT" && docker compose -f "$MELD_COMPOSE" run meld_graph pytest)
    fi
    echo "MELD pytest completed OK."
  fi
elif [[ -n "${MELD_GRAPH_DIR:-}" ]]; then
  echo ""
  echo "  MELD_VERIFY=0 — skipped pytest. To run: MELD_VERIFY=1 $0"
fi

echo ""
echo "== Done =="
