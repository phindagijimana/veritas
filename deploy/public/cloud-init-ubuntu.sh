#!/usr/bin/env bash
# Bootstrap a fresh Ubuntu 24.04 VM into a Veritas-ready state.
#
# Idempotent. Safe to re-run. Requires sudo / root.
#
# What it does:
#   - sets timezone to UTC and enables NTP
#   - installs unattended-upgrades (security patches auto-applied)
#   - installs Docker Engine + Compose plugin
#   - opens ufw for 22, 80, 443 (and nothing else)
#   - creates /srv/veritas as a working directory
#
# After this finishes, see deploy/public/README.md step 2 onward.

set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi

log() { printf '[bootstrap %s] %s\n' "$(date -u +%FT%TZ)" "$*"; }

log "1. apt update + base packages"
DEBIAN_FRONTEND=noninteractive apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl gnupg lsb-release ufw unattended-upgrades \
  git

log "2. timezone + NTP"
timedatectl set-timezone UTC
timedatectl set-ntp true

log "3. unattended security upgrades"
cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF
dpkg-reconfigure -plow unattended-upgrades || true

log "4. Docker Engine + Compose v2"
if ! command -v docker >/dev/null; then
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
    >/etc/apt/sources.list.d/docker.list
  apt-get update -y
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker

log "5. ufw — allow 22 / 80 / 443 only"
ufw allow 22/tcp >/dev/null
ufw allow 80/tcp >/dev/null
ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

log "6. working directory /srv/veritas"
mkdir -p /srv/veritas
chown "${SUDO_USER:-root}":"${SUDO_USER:-root}" /srv/veritas

log "DONE. Next: cd /srv/veritas && git clone https://github.com/phindagijimana/veritas.git"
log "Then follow deploy/public/README.md from step 2."
