from __future__ import annotations

import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent
from app.security.models import Principal

logger = logging.getLogger("atlas.audit")


def record_audit(
    db: Session,
    *,
    actor: Principal,
    action: str,
    resource_type: str,
    resource_id: str,
    detail: Optional[dict[str, Any]] = None,
    staging_id: Optional[str] = None,
) -> AuditEvent:
    row = AuditEvent(
        actor_principal_id=actor.principal_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail_json=json.dumps(detail) if detail else None,
        staging_id=staging_id,
    )
    db.add(row)
    db.flush()
    logger.info(
        "audit action=%s resource=%s:%s actor=%s",
        action,
        resource_type,
        resource_id,
        actor.principal_id,
    )
    return row
