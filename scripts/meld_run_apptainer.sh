#!/usr/bin/env bash
# Run MELD Graph new-patient pipeline on IDEAS/BIDS data using Apptainer (no Docker/Podman).
#
# Use when: podman-compose fails with "insufficient UIDs or GIDs" when pulling images.
# Requires: apptainer (or singularity), license.txt + meld_license.txt in repo root.
#
# First pull may take a long time; image is cached as meld_docker_data/meld_graph.sif
# (or set MELD_SIF to an existing .sif path).
#
# APPTAINER_TMPDIR must be on a filesystem that is executable (not /tmp if noexec) and
# ideally large enough for build temp; default: meld_docker_data/.apptainer_tmp
#
# Usage:
#   export IDEAS_BIDS_ROOT=/path/to/bids_IDEAS
#   export SUBJECT=sub-10   # optional
#   ./scripts/meld_run_apptainer.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

export VALIDATOR_ROOT="${VALIDATOR_ROOT:-$ROOT}"
IDEAS_BIDS_ROOT="${IDEAS_BIDS_ROOT:-/ood/share/datasets/ideas}"
MELD_IMAGE_REF="${MELD_IMAGE_REF:-docker://phindagijimana321/meld_graph:v2.2.4-nir2}"
MELD_SIF="${MELD_SIF:-$ROOT/meld_docker_data/meld_graph.sif}"
TMPDIR="${APPTAINER_TMPDIR:-$ROOT/meld_docker_data/.apptainer_tmp}"
export APPTAINER_TMPDIR="$TMPDIR"
mkdir -p "$APPTAINER_TMPDIR"

SUBJECT_ARG=()
if [[ -n "${SUBJECT:-}" ]]; then
  SUBJECT_ARG=(--subject "$SUBJECT")
fi

echo "== MELD via Apptainer (IDEAS / BIDS) =="
echo "  VALIDATOR_ROOT=$VALIDATOR_ROOT"
echo "  IDEAS_BIDS_ROOT=$IDEAS_BIDS_ROOT"
echo "  APPTAINER_TMPDIR=$APPTAINER_TMPDIR"
echo ""

if [[ ! -d "$IDEAS_BIDS_ROOT" ]]; then
  echo "ERROR: IDEAS_BIDS_ROOT does not exist: $IDEAS_BIDS_ROOT" >&2
  exit 1
fi

if [[ ! -f "$ROOT/license.txt" ]] || [[ ! -f "$ROOT/meld_license.txt" ]]; then
  echo "ERROR: Place FreeSurfer license.txt and meld_license.txt in $ROOT" >&2
  exit 1
fi

if ! command -v apptainer >/dev/null 2>&1; then
  echo "ERROR: apptainer not found in PATH" >&2
  exit 1
fi

python3 "$SCRIPT_DIR/meld_prepare_bids_input.py" --bids-root "$IDEAS_BIDS_ROOT" "${SUBJECT_ARG[@]}" --reset-input

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

IMAGE_RUN="$MELD_IMAGE_REF"
if [[ -f "$MELD_SIF" ]]; then
  IMAGE_RUN="$MELD_SIF"
  echo "Using existing SIF: $IMAGE_RUN"
elif [[ "${MELD_PULL:-1}" == "1" ]]; then
  echo "Pulling image to $MELD_SIF (first run may take 15–30+ minutes)..."
  apptainer pull "$MELD_SIF" "$MELD_IMAGE_REF"
  IMAGE_RUN="$MELD_SIF"
fi

echo ""
echo "Starting MELD (subject=$SUB_ID) — this can take many hours."
echo ""

exec apptainer run --cleanenv \
  --env FS_LICENSE=/run/secrets/license.txt \
  --env MELD_LICENSE=/run/secrets/meld_license.txt \
  -B "$ROOT/meld_docker_data:/data" \
  -B "$ROOT/license.txt:/run/secrets/license.txt:ro" \
  -B "$ROOT/meld_license.txt:/run/secrets/meld_license.txt:ro" \
  "$IMAGE_RUN" \
  python scripts/new_patient_pipeline/new_pt_pipeline.py -id "$SUB_ID" --fastsurfer
