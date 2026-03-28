"""Celery worker entrypoint (replaces RQ worker). Run: python -m app.workers.celery_worker"""

from __future__ import annotations

from app.celery_app import celery_app
from app.core.config import get_settings, validate_production_settings


def main() -> None:
    settings = get_settings()
    validate_production_settings(settings)
    celery_app.worker_main(
        [
            "worker",
            "--loglevel",
            "info",
            "-Q",
            settings.rq_queue_name,
        ]
    )


if __name__ == "__main__":
    main()
