from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text

from app.core.config import get_settings
from app.core.telemetry import ACTIVE_JOBS, REQUEST_COUNT, REQUEST_LATENCY
from app.db.session import SessionLocal
from app.services.job_service import JobService
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/ready")
def readiness() -> dict:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    finally:
        db.close()

    checks: dict[str, str] = {"database": "ok"}
    settings = get_settings()
    if settings.job_queue_enabled:
        try:
            Redis.from_url(settings.redis_url).ping()
            checks["redis"] = "ok"
        except RedisError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Redis unavailable (JOB_QUEUE_ENABLED=true): {exc}",
            ) from exc

    return {"status": "ready", **checks}


@router.get("/metrics")
def metrics() -> Response:
    if not get_settings().prometheus_enabled:
        return Response(status_code=status.HTTP_404_NOT_FOUND)
    db = SessionLocal()
    try:
        summary = JobService.summary(db)
    finally:
        db.close()
    ACTIVE_JOBS.labels(state="queued").set(summary.get("queued", 0))
    ACTIVE_JOBS.labels(state="running").set(summary.get("running", 0))
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
