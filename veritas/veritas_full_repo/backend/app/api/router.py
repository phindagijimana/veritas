from __future__ import annotations

from fastapi import APIRouter

from app.api.routes.admin import router as admin_router
from app.api.routes.atlas import router as atlas_router
from app.api.routes.atlas_execution import router as atlas_execution_router
from app.api.routes.atlas_phase_c import router as atlas_phase_c_router
from app.api.routes.atlas_phase_d import router as atlas_phase_d_router
from app.api.routes.auth import router as auth_router
from app.api.routes.datasets import router as datasets_router
from app.api.routes.health import router as health_router
from app.api.routes.hpc import router as hpc_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.leaderboard import router as leaderboard_router
from app.api.routes.pipelines import router as pipelines_router
from app.api.routes.reports import router as reports_router
from app.api.routes.requests import router as requests_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(atlas_router)
api_router.include_router(atlas_execution_router)
api_router.include_router(atlas_phase_c_router)
api_router.include_router(atlas_phase_d_router)
api_router.include_router(auth_router)
api_router.include_router(datasets_router)
api_router.include_router(pipelines_router)
api_router.include_router(requests_router)
api_router.include_router(jobs_router)
api_router.include_router(reports_router)
api_router.include_router(leaderboard_router)
api_router.include_router(hpc_router)
api_router.include_router(admin_router)
