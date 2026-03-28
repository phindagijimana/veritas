"""Celery application for Atlas async tasks (broker/backend: Redis or memory for dev)."""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings


def _make_celery() -> Celery:
    s = get_settings()
    app = Celery(
        "atlas",
        broker=s.celery_effective_broker,
        backend=s.celery_effective_backend,
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        task_default_queue="atlas",
    )
    return app


celery_app = _make_celery()


@celery_app.task(name="atlas.ping")
def ping_task() -> str:
    return "ok"
