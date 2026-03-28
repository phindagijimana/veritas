from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import get_settings


class LimitRequestBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds max_request_body_bytes (Phase 8)."""

    async def dispatch(self, request: Request, call_next):
        cfg = get_settings()
        if cfg.max_request_body_bytes > 0 and request.method in ("POST", "PUT", "PATCH"):
            cl = request.headers.get("content-length")
            if cl:
                try:
                    if int(cl) > cfg.max_request_body_bytes:
                        return JSONResponse(
                            status_code=413,
                            content={"detail": f"Request body exceeds limit of {cfg.max_request_body_bytes} bytes"},
                        )
                except ValueError:
                    pass
        return await call_next(request)
