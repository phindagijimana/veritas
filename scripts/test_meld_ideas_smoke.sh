#!/usr/bin/env bash
# Smoke test: prepare MELD input from IDEAS-like BIDS (fixture or real IDEAS path), optional container run.
#
# Usage (from validator repo root):
#   ./scripts/test_meld_ideas_smoke.sh
#   IDEAS_BIDS_ROOT=/ood/share/datasets/ideas SUBJECT=sub-01 ./scripts/test_meld_ideas_smoke.sh
#
# Optional: RUN_MELD_CONTAINER=1 runs docker compose after prepare (needs working Docker + pulled image).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

export VALIDATOR_ROOT="${VALIDATOR_ROOT:-$ROOT}"

IDEAS_BIDS_ROOT="${IDEAS_BIDS_ROOT:-$ROOT/scripts/fixtures/ideas_minimal_bids}"
SUBJECT_ARGS=()
if [[ -n "${SUBJECT:-}" ]]; then
  SUBJECT_ARGS=(--subject "$SUBJECT")
fi

echo "== MELD + IDEAS smoke (prepare input) =="
echo "  VALIDATOR_ROOT=$VALIDATOR_ROOT"
echo "  IDEAS_BIDS_ROOT=$IDEAS_BIDS_ROOT"
echo ""

if [[ ! -d "$IDEAS_BIDS_ROOT" ]]; then
  echo "ERROR: BIDS root not found: $IDEAS_BIDS_ROOT" >&2
  echo "Set IDEAS_BIDS_ROOT to your IDEAS dataset (e.g. /ood/share/datasets/ideas)." >&2
  exit 1
fi

if [[ ! -f "$ROOT/license.txt" ]] || [[ ! -f "$ROOT/meld_license.txt" ]]; then
  echo "WARN: Missing license.txt or meld_license.txt in $ROOT — required for docker MELD run (not for prepare)." >&2
fi

python3 "$SCRIPT_DIR/meld_prepare_bids_input.py" --bids-root "$IDEAS_BIDS_ROOT" "${SUBJECT_ARGS[@]}" --reset-input

INPUT="$ROOT/meld_docker_data/input"
for f in meld_bids_config.json dataset_description.json; do
  if [[ ! -f "$INPUT/$f" ]]; then
    echo "ERROR: Expected file missing: $INPUT/$f" >&2
    exit 1
  fi
done
if ! ls -d "$INPUT"/sub-* &>/dev/null; then
  echo "ERROR: No subject symlink under $INPUT" >&2
  exit 1
fi

echo ""
echo "OK: MELD input prepared under $ROOT/meld_docker_data/"
echo ""

if [[ "${RUN_MELD_CONTAINER:-0}" != "1" ]]; then
  echo "Skipping container (set RUN_MELD_CONTAINER=1 to run MELD; may take hours on real data)."
  echo "Manual run:"
  echo "  export VALIDATOR_ROOT=\"$ROOT\" DOCKER_USER=\"\$(id -u):\$(id -g)\""
  echo "  docker compose -f scripts/meld-compose.validator.yml run --rm meld_graph \\"
  echo "    python scripts/new_patient_pipeline/new_pt_pipeline.py -id <sub-id> --fastsurfer"
  exit 0
fi

if [[ ! -f "$ROOT/license.txt" ]] || [[ ! -f "$ROOT/meld_license.txt" ]]; then
  echo "ERROR: license.txt and meld_license.txt required in $ROOT for container run." >&2
  exit 1
fi

SUB_ID=""
if [[ -n "${SUBJECT:-}" ]]; then
  SUB_ID="$SUBJECT"
  [[ "$SUB_ID" == sub-* ]] || SUB_ID="sub-$SUB_ID"
else
  for d in "$INPUT"/sub-*; do
    [[ -e "$d" ]] || continue
    SUB_ID="$(basename "$d")"
    break
  done
fi
export DOCKER_USER="${DOCKER_USER:-$(id -u):$(id -g)}"
echo "Starting MELD container for subject=$SUB_ID ..."
exec docker compose -f "$ROOT/scripts/meld-compose.validator.yml" run --rm meld_graph \
  python scripts/new_patient_pipeline/new_pt_pipeline.py -id "$SUB_ID" --fastsurfer
