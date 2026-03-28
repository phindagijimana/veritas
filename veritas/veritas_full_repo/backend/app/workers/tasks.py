"""Enqueue Celery jobs (public API for routes and services)."""

from __future__ import annotations

from app.workers.celery_tasks import run_job_monitor_sweep_task, run_report_generation_task


def enqueue_report_generation(request_id: int) -> str:
    return run_report_generation_task.delay(request_id).id


def enqueue_job_monitor_sweep() -> str:
    return run_job_monitor_sweep_task.delay().id