"""Celery application for Veritas async jobs (replaces RQ)."""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings


def _make_celery() -> Celery:
    s = get_settings()
    app = Celery(
        "veritas",
        broker=s.redis_url,
        backend=s.redis_url,
        include=["app.workers.celery_tasks"],
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        task_default_queue=s.rq_queue_name,
        task_soft_time_limit=s.rq_job_timeout_seconds,
    )
    return app


celery_app = _make_celery()

# Register tasks when the worker or API imports this module (include= alone loads tasks in the worker only).
import app.workers.celery_tasks  # noqa: E402, F401
