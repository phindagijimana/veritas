#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/var/veritas_artifacts
python -m app.workers.runner &
exec rq worker ai-biomarkers
