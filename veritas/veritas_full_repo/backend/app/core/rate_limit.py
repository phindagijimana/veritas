from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import get_settings


def rate_limit_key(request: Request) -> str:
    if get_settings().rate_limit_trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Per-process limits; use Redis-backed storage later for multi-replica deployments.
limiter = Limiter(key_func=rate_limit_key, default_limits=["200/minute"], headers_enabled=True)
