"""Optional in-process sliding-window rate limit for /api/v1/admin/* (single-worker; use a gateway for HA)."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings


def _client_host(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


class AdminRateLimitMiddleware(BaseHTTPMiddleware):
    """Limits requests per client IP per minute to paths under ``{api_prefix}/admin``."""

    def __init__(self, app, limit_per_minute: int) -> None:
        super().__init__(app)
        self._limit = limit_per_minute
        self._lock = asyncio.Lock()
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if self._limit <= 0:
            return await call_next(request)

        settings = get_settings()
        prefix = f"{settings.api_prefix.rstrip('/')}/admin"
        path = request.url.path
        if not path.startswith(prefix):
            return await call_next(request)

        host = _client_host(request)
        now = time.monotonic()
        window = 60.0

        async with self._lock:
            q = self._hits[host]
            while q and (now - q[0]) > window:
                q.popleft()
            if len(q) >= self._limit:
                return JSONResponse(
                    {"detail": "Too many admin requests; slow down or configure gateway limits"},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
            q.append(now)

        response: Response = await call_next(request)
        return response
