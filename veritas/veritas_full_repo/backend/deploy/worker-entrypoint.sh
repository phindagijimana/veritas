#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/var/veritas_artifacts
python -m app.workers.runner &
exec celery -A app.celery_app worker --loglevel=info -Q "${RQ_QUEUE_NAME:-ai-biomarkers}"
