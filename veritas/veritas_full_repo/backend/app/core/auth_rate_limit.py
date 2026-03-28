"""
Stricter rate limits for POST /auth/login and /auth/register without wrapping route handlers.

SlowAPI's @limiter.limit decorator breaks FastAPI JSON body binding for those routes; the global
SlowAPIMiddleware still applies default_limits. This middleware adds per-endpoint limits using the
same client key as app.core.rate_limit.rate_limit_key.
"""

from __future__ import annotations

import logging
import time
from functools import lru_cache

from limits import parse
from limits.storage import memory
from limits.strategies import MovingWindowRateLimiter
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.rate_limit import rate_limit_key

logger = logging.getLogger(__name__)

_storage = memory.MemoryStorage()
_strategy = MovingWindowRateLimiter(_storage)


def reset_auth_rate_limit_storage() -> None:
    """Clear in-memory counters (for tests)."""
    _storage.reset()


def clear_auth_rate_limit_caches() -> None:
    """Reset storage and parsed limit strings (call after changing env in tests)."""
    reset_auth_rate_limit_storage()
    _parsed_limit.cache_clear()


@lru_cache(maxsize=32)
def _parsed_limit(limit_str: str):
    s = (limit_str or "").strip()
    if not s:
        return None
    try:
        return parse(s)
    except ValueError as e:
        logger.error("Invalid rate limit string %r: %s", limit_str, e)
        return None


def _auth_paths(settings) -> tuple[str, str]:
    prefix = (settings.api_v1_prefix or "").rstrip("/")
    login_p = f"{prefix}/auth/login"
    register_p = f"{prefix}/auth/register"
    return login_p, register_p


def _too_many_response(item, key: str, label: str) -> JSONResponse:
    stats = _strategy.get_window_stats(item, key)
    retry = max(1, int(stats.reset_time - time.time()) + 1)
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded ({label}). Try again later."},
        headers={"Retry-After": str(retry)},
    )


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method != "POST":
            return await call_next(request)

        settings = get_settings()
        login_path, register_path = _auth_paths(settings)
        path = request.url.path.rstrip("/") or "/"
        norm_login = login_path.rstrip("/") or "/"
        norm_register = register_path.rstrip("/") or "/"

        item = None
        bucket = ""
        if path == norm_login:
            item = _parsed_limit(settings.auth_login_rate_limit)
            bucket = "login"
        elif path == norm_register:
            item = _parsed_limit(settings.auth_register_rate_limit)
            bucket = "register"

        if item is None:
            return await call_next(request)

        client_key = rate_limit_key(request)
        limit_key = f"auth-{bucket}:{client_key}"
        if not _strategy.hit(item, limit_key):
            return _too_many_response(item, limit_key, bucket)

        return await call_next(request)
