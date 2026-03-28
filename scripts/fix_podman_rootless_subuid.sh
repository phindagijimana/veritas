#!/usr/bin/env bash
# One-time fix for Podman rootless: "insufficient UIDs or GIDs" when pulling images.
# Requires sudo. Safe to re-run (skips if entries already exist).
#
# Your user must have lines in /etc/subuid and /etc/subgid (see `man subuid`).
# This script appends a non-overlapping range after the common 100000:65536 block.
#
# Usage: sudo ./scripts/fix_podman_rootless_subuid.sh
#    or: curl ... | sudo bash   (not recommended; review first)
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi

# Match passwd login name (may contain @ on some IdM systems)
USER_NAME="${SUDO_USER:-}"
if [[ -z "$USER_NAME" ]]; then
  echo "SUDO_USER is empty; set TARGET_USER=name ./scripts/fix_podman_rootless_subuid.sh" >&2
  exit 1
fi

SUBUID_FILE=/etc/subuid
SUBGID_FILE=/etc/subgid
# After 100000:65536 (ends at 165535), use 165536:65536
RANGE_START=165536
RANGE_COUNT=65536

ensure_line() {
  local file="$1"
  local line="$2"
  if [[ -f "$file" ]] && grep -qF "${USER_NAME}:" "$file" 2>/dev/null; then
    echo "Already present in $file: $(grep "^${USER_NAME}:" "$file")"
    return 0
  fi
  echo "$line" >>"$file"
  echo "Appended to $file: $line"
}

ensure_line "$SUBUID_FILE" "${USER_NAME}:${RANGE_START}:${RANGE_COUNT}"
ensure_line "$SUBGID_FILE" "${USER_NAME}:${RANGE_START}:${RANGE_COUNT}"

# Apply new mappings to existing rootless storage
if command -v podman >/dev/null 2>&1; then
  sudo -u "$USER_NAME" podman system migrate 2>/dev/null || true
fi

echo "Done. Log out and back in (or start a new session), then: podman info"
echo "Optional: rm -rf ~/.local/share/containers/storage (only if you want a clean store; destroys cached images)."
