from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.routes.datasets import router as datasets_router
from app.api.routes.security_demo import router as security_demo_router
from app.api.routes.staging import router as staging_router
from app.bootstrap import run_startup
from app.core.config import get_settings
from app.db.session import get_engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    run_startup()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="1.3.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict:
        db_status = "unknown"
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            db_status = "ok"
        except Exception:
            db_status = "error"
        return {
            "status": "ok",
            "env": settings.env,
            "auth_mode": settings.auth_mode,
            "database": db_status,
        }

    if settings.security_demo_enabled:
        app.include_router(security_demo_router, prefix=settings.api_prefix)
    app.include_router(datasets_router, prefix=settings.api_prefix)
    app.include_router(staging_router, prefix=settings.api_prefix)
    return app


app = create_app()
