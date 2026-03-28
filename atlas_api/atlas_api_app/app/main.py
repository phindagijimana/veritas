from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from starlette.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.datasets import router as datasets_router
from app.api.routes.security_demo import router as security_demo_router
from app.api.routes.staging import router as staging_router
from app.bootstrap import run_startup
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.db.session import get_engine
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.admin_rate_limit import AdminRateLimitMiddleware
from app.middleware.request_id import RequestIdMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_startup()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(title=settings.app_name, version="1.4.0", lifespan=lifespan)

    # Middleware order (last registered runs first on incoming requests): CORS → request ID → access log → admin limiter
    if settings.admin_rate_limit_per_minute > 0:
        app.add_middleware(
            AdminRateLimitMiddleware,
            limit_per_minute=settings.admin_rate_limit_per_minute,
        )
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIdMiddleware)
    origins = settings.cors_origin_list()
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health")
    async def health() -> dict:
        """Liveness: process is up (use for Kubernetes livenessProbe)."""
        return {"status": "ok"}

    @app.get("/ready")
    async def ready() -> JSONResponse:
        """Readiness: database required; Redis and S3 checked when configured."""
        content: dict = {"status": "ready", "env": settings.env}
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            content["database"] = "ok"
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "database": "error"},
            )

        if (settings.redis_url or "").strip():
            try:
                from redis import Redis
                from redis.exceptions import RedisError

                Redis.from_url(settings.redis_url).ping()
                content["redis"] = "ok"
            except RedisError:
                return JSONResponse(
                    status_code=503,
                    content={**content, "status": "not_ready", "redis": "error"},
                )

        if settings.s3_configured:
            try:
                from app.integrations.object_storage import check_s3_health

                check_s3_health()
                content["s3"] = "ok"
            except Exception:
                return JSONResponse(
                    status_code=503,
                    content={**content, "status": "not_ready", "s3": "error"},
                )

        return JSONResponse(status_code=200, content=content)

    if settings.security_demo_enabled:

        @app.middleware("http")
        async def _security_demo_deprecation(request, call_next):  # type: ignore[no-untyped-def]
            response = await call_next(request)
            path = request.url.path
            if path.startswith(f"{settings.api_prefix}/security-demo"):
                response.headers["Deprecation"] = "true"
                response.headers["Warning"] = '299 - "security-demo is for development; disable ATLAS_SECURITY_DEMO_ENABLED in production"'
            return response

        app.include_router(security_demo_router, prefix=settings.api_prefix)
    app.include_router(admin_router, prefix=settings.api_prefix)
    app.include_router(datasets_router, prefix=settings.api_prefix)
    app.include_router(staging_router, prefix=settings.api_prefix)

    if settings.metrics_enabled:
        Instrumentator(
            excluded_handlers=["/health", "/ready", "/metrics"],
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    return app


app = create_app()
