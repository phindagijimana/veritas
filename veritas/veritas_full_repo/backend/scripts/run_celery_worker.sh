#!/usr/bin/env bash
# Celery worker for async job monitor sweeps and report generation.
set -euo pipefail
cd "$(dirname "$0")/.."
exec python3 -m app.workers.celery_worker "$@"
