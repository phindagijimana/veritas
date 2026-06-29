# Public deploy starter — Caddy + docker-compose

This is the "give me a fresh VM and a DNS A-record, and I want
`https://veritas.example.com` answering" path. It overlays the existing
`backend/docker-compose.prod.yml` with a Caddy reverse proxy that
terminates TLS using Let's Encrypt and proxies to the existing nginx +
backend stack.

## What you need

1. A **VM** running Ubuntu 24.04 LTS (or any Linux with Docker
   Engine + Compose v2 installed). 2 vCPU / 4 GB RAM is a comfortable
   floor; the backend is the bottleneck, not the proxy.
2. A **DNS A-record** for the hostname you want (`veritas.example.com`)
   pointing to the VM's public IP.
3. Ports **80** and **443** open from the public internet to the VM
   (Caddy needs both for the ACME HTTP-01 challenge and to serve
   traffic).
4. A **secrets bundle** (`.env.production` populated from
   `.env.production.example` at the repo root). At minimum:
   `AUTH_SECRET_KEY`, `DATABASE_URL`, `ALLOWED_ORIGINS`, the
   `EMAIL_*` block, and `ATLAS_API_CLIENT_SECRET`.

## Zero-to-deployed

```bash
# 1. On a fresh VM (Ubuntu 24.04):
sudo bash deploy/public/cloud-init-ubuntu.sh

# 2. Clone the repo and populate secrets
git clone https://github.com/phindagijimana/veritas.git
cd veritas
cp .env.production.example veritas/veritas_full_repo/backend/.env.production
$EDITOR veritas/veritas_full_repo/backend/.env.production

# 3. Point the deploy at your hostname + email
export VERITAS_HOSTNAME=veritas.example.com
export VERITAS_LE_EMAIL=ops@example.com

# 4. Boot the public stack
cd veritas/veritas_full_repo/backend
docker compose \
  -f docker-compose.prod.yml \
  -f ../../../deploy/public/docker-compose.public.yml \
  up -d

# 5. Watch Caddy fetch the first cert (15–30s on a healthy VM)
docker compose logs -f caddy
```

Within ~30 seconds you should be able to hit `https://veritas.example.com`
and see the Veritas UI. Caddy renews the certificate automatically.

## What this is NOT

- An institutional deployment. You still need to put the VM behind your
  VPN or institutional WAF if PHI is involved.
- A horizontally-scaled deployment. This is a single-host stack
  appropriate for a pilot or a small lab. For larger deployments you
  want the backend, worker, beat, and Redis on separate hosts behind a
  managed load balancer; that's a different deploy.
- A DR plan. Pair this with `scripts/dr_drill.sh` and
  `scripts/backup_postgres.sh` on cron.

## Files in this directory

| File | Purpose |
|------|---------|
| `docker-compose.public.yml` | Overlay that adds Caddy + ACME volumes in front of the existing stack |
| `Caddyfile` | Caddy configuration — HTTPS for `VERITAS_HOSTNAME`, reverse-proxy to the nginx service, gzip + sane headers |
| `cloud-init-ubuntu.sh` | One-shot Ubuntu 24.04 bootstrap: Docker, Docker Compose, unattended-upgrades, ufw, timezone |
| `README.md` | This file |

## Going further

- For an institutional rollout, swap Caddy for nginx-with-cert-manager
  on Kubernetes, or terminate TLS at your institutional load balancer
  and disable Caddy here.
- For S3-backed report storage, set `STORAGE_BACKEND=s3` + the
  `S3_*` env vars in `.env.production` and the backend will write
  artifacts to your bucket instead of the local volume.
- For OIDC SSO, set `AUTH_MODE=oidc` once the wiring lands in v0.2.0
  (currently scaffolded, not yet wired).
