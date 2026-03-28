#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/var/veritas_artifacts
alembic upgrade head || true
exec uvicorn app.main:app --host 0.0.0.0 --port 6000
