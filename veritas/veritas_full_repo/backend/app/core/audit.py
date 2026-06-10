"""Audit-log middleware: persist a row for every state-changing API call.

Captures who (from the Authorization header — JWT or PAT), what (HTTP method
+ route), the subject identifier when present in the path, and the response
status. Never raises into the request path: a failure to log is logged to
stderr but the user's request still completes.
"""
from __future__ import annotations

import logging
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.api_tokens import hash_token, looks_like_pat
from app.core.config import get_settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths whose body is sensitive (password material, etc.) — never store the
# body or its size, just the action.
_REDACT_PATHS = (
    "/auth/login",
    "/auth/register",
    "/auth/tokens",
    "/admin/users/",
)


def _extract_actor(authorization: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (email, role, auth_method) from the bearer header without raising."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None, None, None
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None, None, None
    if looks_like_pat(token):
        db: Session = SessionLocal()
        try:
            from app.models.api_token import ApiToken
            from app.models.user import User

            row = db.query(ApiToken).filter(ApiToken.token_hash == hash_token(token)).one_or_none()
            if row is None:
                return None, None, "pat"
            user = db.query(User).filter(User.id == row.user_id).one_or_none()
            return (user.email if user else None, user.role if user else None, "pat")
        except Exception:
            return None, None, "pat"
        finally:
            db.close()
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.auth_secret_key,
            algorithms=[settings.auth_algorithm],
            options={"require": ["exp", "sub"]},
        )
        return str(payload.get("sub")), str(payload.get("role") or ""), "jwt"
    except JWTError:
        return None, None, "jwt"


def _subject_from_path(method: str, path: str) -> tuple[Optional[str], Optional[str]]:
    """Best-effort (subject_type, subject_id) extraction from a write route's URL.

    Action routes encode the subject in the path:
        POST /jobs/submit/REQ-42   → (request, REQ-42)
        POST /jobs/42/cancel       → (job, 42)
        DELETE /auth/tokens/3      → (api_token, 3)
        PATCH /admin/users/.../role → (user, alice@x)
    """
    p = path.rstrip("/")
    # /api/v1 prefix is stripped by FastAPI before we see it.
    if "/auth/tokens" in p:
        parts = p.rsplit("/", 1)
        if parts[-1] and parts[-1] != "tokens":
            return "api_token", parts[-1]
        return "api_token", None
    if "/admin/users/" in p:
        # /admin/users/{email}/role or /reset-password
        slug = p.split("/admin/users/", 1)[1].split("/", 1)[0]
        return "user", slug
    if "/requests/" in p:
        slug = p.split("/requests/", 1)[1].split("/", 1)[0]
        return "request", slug
    if "/jobs/submit/" in p or "/jobs/preview/" in p:
        slug = p.split("/jobs/", 1)[1].split("/", 1)[1]
        return "request", slug
    if "/jobs/" in p:
        slug = p.split("/jobs/", 1)[1].split("/", 1)[0]
        return "job", slug
    if "/leaderboard/push/" in p:
        slug = p.split("/leaderboard/push/", 1)[1].split("/", 1)[0]
        return "request", slug
    if "/reports/generate/" in p or "/reports/publish/" in p:
        slug = p.rsplit("/", 1)[-1]
        return "request", slug
    return None, None


def _action_from_route(method: str, path: str) -> str:
    """A short stable name for the action, suitable for filtering."""
    p = path.split("?", 1)[0]
    if p.endswith("/auth/login"):
        return "auth.login"
    if p.endswith("/auth/register"):
        return "auth.register"
    if "/auth/tokens" in p and method == "POST":
        return "auth.token.create"
    if "/auth/tokens" in p and method == "DELETE":
        return "auth.token.revoke"
    if "/admin/users" in p and "reset-password" in p:
        return "admin.user.reset_password"
    if "/admin/users" in p and "/role" in p:
        return "admin.user.set_role"
    if p.endswith("/pipelines") and method == "POST":
        return "pipeline.create"
    if p.endswith("/datasets") and method == "POST":
        return "dataset.create"
    if "/hpc/connect" in p:
        return "hpc.connect"
    if "/hpc/test-connection" in p:
        return "hpc.test_connection"
    if "/jobs/preview/" in p:
        return "job.preview"
    if "/jobs/submit/" in p:
        return "job.submit"
    if "/jobs/" in p and p.endswith("/cancel"):
        return "job.cancel"
    if "/jobs/" in p and p.endswith("/advance"):
        return "job.advance"
    if "/jobs/" in p and p.endswith("/sync"):
        return "job.sync"
    if "/jobs/monitor/sweep" in p:
        return "job.monitor.sweep"
    if "/leaderboard/push" in p:
        return "leaderboard.push"
    if "/reports/generate" in p:
        return "report.generate"
    if "/reports/publish" in p:
        return "report.publish"
    if "/requests" in p and "/status" in p:
        return "request.status.set"
    if "/requests" in p and method == "POST":
        return "request.create"
    if "/atlas/phase-c" in p or "/atlas/phase-d" in p or "/atlas-execution" in p:
        return f"atlas.{method.lower()}"
    return f"{method.lower()}.{p.lstrip('/')}"


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        try:
            method = request.method.upper()
            path = request.url.path
            # Only write methods on /api/v1/* (skip /static, /health, /metrics).
            if method not in _WRITE_METHODS or not path.startswith("/api/"):
                return response
            email, role, auth_method = _extract_actor(request.headers.get("authorization"))
            action = _action_from_route(method, path)
            subject_type, subject_id = _subject_from_path(method, path)
            detail = None  # we never record bodies; redact paths above documented for grep
            db: Session = SessionLocal()
            try:
                from app.models.audit_event import AuditEvent

                ip = request.client.host if request.client else None
                db.add(
                    AuditEvent(
                        actor_email=email,
                        actor_role=role,
                        auth_method=auth_method,
                        action=action,
                        subject_type=subject_type,
                        subject_id=subject_id,
                        http_status=response.status_code,
                        route=f"{method} {path}",
                        ip=ip,
                        detail=detail,
                    )
                )
                db.commit()
            finally:
                db.close()
        except Exception as exc:  # pragma: no cover — never fail the request because logging blew up
            logger.warning("audit middleware failed: %s", exc)
        return response


__all__ = ["AuditMiddleware"]
