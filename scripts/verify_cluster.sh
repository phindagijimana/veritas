#!/usr/bin/env bash
# Cluster-side preflight for a Veritas deployment.
#
# Run this on the Slurm head node (or anywhere Veritas's SSH user will
# land via the SSH_REMOTE_HOST / SSH_REMOTE_USER pair) to verify the
# eight assumptions Veritas makes about a cluster. Each check is
# independent; the script keeps going on failure and prints a summary
# at the end. Exit code is the number of failed checks (0 = clean).
#
# Usage:
#   verify_cluster.sh                              # use defaults
#   verify_cluster.sh --workdir ~/veritas/jobs --license-dir /shared/freesurfer
#   verify_cluster.sh --api-url https://veritas.example.com   # check reachability too

set -uo pipefail

WORKDIR="${SLURM_REMOTE_WORKDIR:-$HOME/veritas/jobs}"
LICENSE_DIR="${MELD_LICENSE_HOST_DIR:-/shared/freesurfer}"
STAGING="${DATASET_STAGING_ROOT:-/scratch/veritas/staging}"
API_URL=""
ENGINE="${RUNTIME_ENGINE:-apptainer}"
TEST_IMAGE="docker://ghcr.io/meld-graph/meld-graph:v2.2.4-nir2"
PASS=0; FAIL=0; WARN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workdir) WORKDIR="$2"; shift 2 ;;
    --license-dir) LICENSE_DIR="$2"; shift 2 ;;
    --staging) STAGING="$2"; shift 2 ;;
    --api-url) API_URL="$2"; shift 2 ;;
    --engine) ENGINE="$2"; shift 2 ;;
    --test-image) TEST_IMAGE="$2"; shift 2 ;;
    -h|--help)
      cat <<USAGE
Usage: $0 [options]
  --workdir DIR        scratch sbatch working dir (default $WORKDIR)
  --license-dir DIR    host dir with FreeSurfer + MELD licenses (default $LICENSE_DIR)
  --staging DIR        Atlas dataset staging root (default $STAGING)
  --api-url URL        if set, curl-check the API is reachable from here
  --engine NAME        apptainer | singularity | docker (default $ENGINE)
  --test-image IMAGE   container image to test-pull (default $TEST_IMAGE)
USAGE
      exit 0 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*"; FAIL=$((FAIL+1)); }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; WARN=$((WARN+1)); }
hdr()  { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }

# ---------- 1. Slurm presence ---------------------------------------------
hdr "1. Slurm"
if command -v sbatch >/dev/null && command -v squeue >/dev/null && command -v scancel >/dev/null; then
  V=$(sbatch --version 2>/dev/null | head -n1)
  ok "sbatch / squeue / scancel on PATH ($V)"
else
  bad "sbatch, squeue, or scancel missing from PATH"
fi

if squeue -h >/dev/null 2>&1; then
  ok "squeue is reachable (slurmctld responding)"
else
  bad "squeue failed — slurmctld not reachable from this host"
fi

# ---------- 2. Container runtime ------------------------------------------
hdr "2. Container runtime ($ENGINE)"
case "$ENGINE" in
  apptainer)
    if command -v apptainer >/dev/null; then ok "apptainer on PATH ($(apptainer --version))"; else bad "apptainer not on PATH"; fi
    ;;
  singularity)
    if command -v singularity >/dev/null; then ok "singularity on PATH ($(singularity --version))"; else bad "singularity not on PATH"; fi
    ;;
  docker)
    if command -v docker >/dev/null; then ok "docker on PATH ($(docker --version))"; else bad "docker not on PATH"; fi
    ;;
  *) bad "unknown engine: $ENGINE" ;;
esac

# ---------- 3. License files ----------------------------------------------
hdr "3. FreeSurfer + MELD license"
if [[ -d "$LICENSE_DIR" ]]; then
  ok "license dir exists: $LICENSE_DIR"
  for f in license.txt meld_license.txt; do
    if [[ -s "$LICENSE_DIR/$f" ]]; then
      ok "  $f present and non-empty"
    else
      bad "  $f missing or empty in $LICENSE_DIR"
    fi
  done
  # Permission sanity: must be readable, must NOT be world-writable
  MODE=$(stat -c '%a' "$LICENSE_DIR" 2>/dev/null || echo "?")
  if [[ "$MODE" =~ ^7..$ ]] && [[ "${MODE:1:1}" =~ ^[02]$ ]] && [[ "${MODE:2:1}" =~ ^[02]$ ]]; then
    ok "  permissions $MODE look safe (owner rw, others r at most)"
  else
    warn "  permissions on $LICENSE_DIR are $MODE — recommend 0750 or stricter"
  fi
else
  bad "license dir does not exist: $LICENSE_DIR (set MELD_LICENSE_HOST_DIR)"
fi

# ---------- 4. Scratch + working dirs -------------------------------------
hdr "4. Scratch + working directories"
for d in "$WORKDIR" "$STAGING"; do
  if [[ -d "$d" ]]; then
    if [[ -w "$d" ]]; then
      ok "$d exists and is writable by $(whoami)"
    else
      bad "$d exists but is not writable by $(whoami)"
    fi
  else
    # Try to create it (it's expected to be created on first use)
    if mkdir -p "$d" 2>/dev/null; then
      ok "$d did not exist; created it"
    else
      bad "$d does not exist and could not be created"
    fi
  fi
done

# ---------- 5. Disk quota --------------------------------------------------
hdr "5. Disk space"
if df -h "$WORKDIR" 2>/dev/null | awk 'NR==2 { print $4 }' | grep -qE '^[1-9][0-9]+G|^[0-9]+T'; then
  ok "$WORKDIR free: $(df -h "$WORKDIR" | awk 'NR==2 {print $4}')"
else
  warn "$WORKDIR has less than 10 GB free — long MELD runs may stall"
fi

# ---------- 6. Container pull dry-run -------------------------------------
hdr "6. Container pull dry-run"
if [[ "$ENGINE" == "apptainer" ]] || [[ "$ENGINE" == "singularity" ]]; then
  CACHE_DIR="${APPTAINER_CACHEDIR:-$HOME/.apptainer/cache}"
  ok "container cache: $CACHE_DIR"
  warn "skipping actual pull of $TEST_IMAGE (slow, expensive); run manually:"
  printf '       %s pull --disable-cache --tmpdir /tmp /tmp/test.sif %s\n' "$ENGINE" "$TEST_IMAGE"
else
  warn "skipping pull test for engine=$ENGINE"
fi

# ---------- 7. API reachability from cluster ------------------------------
hdr "7. API reachability"
if [[ -n "$API_URL" ]]; then
  if curl -fsS --max-time 10 "$API_URL/health" > /dev/null; then
    ok "$API_URL/health is reachable from this host"
  else
    bad "$API_URL/health unreachable — check firewall / routing"
  fi
else
  warn "no --api-url given; skipping reachability check"
fi

# ---------- 8. Time sync ---------------------------------------------------
hdr "8. Time sync"
if command -v timedatectl >/dev/null; then
  if timedatectl show -p NTPSynchronized --value 2>/dev/null | grep -q yes; then
    ok "NTP synchronized"
  else
    warn "NTP not synchronized — audit-log timestamps may drift relative to the API host"
  fi
else
  warn "timedatectl unavailable; cannot check NTP from here"
fi

# ---------- summary -------------------------------------------------------
hdr "Summary"
printf '  passed: %d   warnings: %d   failed: %d\n' "$PASS" "$WARN" "$FAIL"
exit "$FAIL"
