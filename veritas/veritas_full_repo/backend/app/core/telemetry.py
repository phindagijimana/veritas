from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter("veritas_http_requests_total", "HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("veritas_http_request_duration_seconds", "HTTP latency", ["method", "path"])
ACTIVE_JOBS = Gauge("veritas_active_jobs", "Active jobs by state", ["state"])
DATASET_VALIDATION_COUNT = Counter("veritas_dataset_validations_total", "Dataset validation runs", ["status"])
