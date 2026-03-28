#!/usr/bin/env bash
# Run MELD Graph new-patient pipeline on T1w-only data from the IDEAS BIDS tree (or any BIDS root).
#
# Atlas registry: dataset_id=ideas, secondary OOD path (typical): /ood/share/datasets/ideas
# Override if your copy lives elsewhere (e.g. Veritas staging).
#
# Requires: license.txt + meld_license.txt in validator repo root; Docker/Podman.
#
# Usage:
#   export IDEAS_BIDS_ROOT=/ood/share/datasets/ideas
#   export SUBJECT=sub-01          # optional
#   ./scripts/meld_run_ideas_t1.sh
#
# References:
#   https://meld-graph.readthedocs.io/en/latest/run_prediction_pipeline.html
#   https://meld-graph.readthedocs.io/en/latest/prepare_data.html

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

export VALIDATOR_ROOT="${VALIDATOR_ROOT:-$ROOT}"

IDEAS_BIDS_ROOT="${IDEAS_BIDS_ROOT:-/ood/share/datasets/ideas}"
SUBJECT_ARG=()
if [[ -n "${SUBJECT:-}" ]]; then
  SUBJECT_ARG=(--subject "$SUBJECT")
fi

echo "== MELD T1 pipeline (IDEAS / BIDS) =="
echo "  VALIDATOR_ROOT=$VALIDATOR_ROOT"
echo "  IDEAS_BIDS_ROOT=$IDEAS_BIDS_ROOT"
echo ""

if [[ ! -d "$IDEAS_BIDS_ROOT" ]]; then
  echo "ERROR: IDEAS_BIDS_ROOT does not exist: $IDEAS_BIDS_ROOT" >&2
  echo "Set IDEAS_BIDS_ROOT to your IDEAS BIDS root (Atlas secondary ref for 'ideas' is often /ood/share/datasets/ideas)." >&2
  exit 1
fi

if [[ ! -f "$ROOT/license.txt" ]] || [[ ! -f "$ROOT/meld_license.txt" ]]; then
  echo "ERROR: Place FreeSurfer license.txt and meld_license.txt in $ROOT" >&2
  exit 1
fi

python3 "$SCRIPT_DIR/meld_prepare_bids_input.py" --bids-root "$IDEAS_BIDS_ROOT" "${SUBJECT_ARG[@]}" --reset-input

export DOCKER_USER="${DOCKER_USER:-$(id -u):$(id -g)}"

# Optional pull
if [[ "${MELD_PULL:-0}" == "1" ]]; then
  docker pull meldproject/meld_graph:latest
fi

# Subject id: env or first sub-* under input/
SUB_ID=""
if [[ -n "${SUBJECT:-}" ]]; then
  SUB_ID="$SUBJECT"
  [[ "$SUB_ID" == sub-* ]] || SUB_ID="sub-$SUB_ID"
else
  for d in "$ROOT/meld_docker_data/input"/sub-*; do
    [[ -e "$d" ]] || continue
    SUB_ID="$(basename "$d")"
    break
  done
fi
if [[ -z "$SUB_ID" ]]; then
  echo "ERROR: Could not determine subject under meld_docker_data/input" >&2
  exit 1
fi

echo ""
echo "Starting MELD pipeline (this can take many hours): subject=$SUB_ID"
echo ""

exec docker compose -f "$ROOT/scripts/meld-compose.validator.yml" run --rm meld_graph \
  python scripts/new_patient_pipeline/new_pt_pipeline.py -id "$SUB_ID" --fastsurfer
