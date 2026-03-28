from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from fastapi import HTTPException, status

from app.core.enums import AccessLevel, DatasetVisibility, ResourceAction
from app.security.models import Principal


@dataclass
class PermissionGrant:
    principal_type: str
    principal_id: str
    access_level: str


@dataclass
class ResourceContext:
    resource_id: str
    dataset_visibility: DatasetVisibility = DatasetVisibility.PUBLIC
    owner_principal_id: str | None = None
    grants: list[PermissionGrant] | None = None


def _has_grant(principal: Principal, grants: Iterable[PermissionGrant], accepted: set[str]) -> bool:
    for grant in grants:
        if grant.principal_type != principal.principal_type.value:
            continue
        if grant.principal_id != principal.principal_id:
            continue
        if grant.access_level in accepted:
            return True
    return False


def is_allowed(principal: Principal, action: ResourceAction, context: ResourceContext) -> bool:
    if principal.is_internal or principal.is_admin:
        return True

    grants = context.grants or []

    if action == ResourceAction.DATASET_READ:
        if context.dataset_visibility == DatasetVisibility.PUBLIC:
            return True
        return _has_grant(principal, grants, {AccessLevel.READ.value, AccessLevel.WRITE.value, AccessLevel.ADMIN.value})

    if action == ResourceAction.EXECUTION_CREATE:
        if context.dataset_visibility == DatasetVisibility.PUBLIC:
            return True
        return _has_grant(principal, grants, {AccessLevel.WRITE.value, AccessLevel.ADMIN.value})

    if action == ResourceAction.DATASET_WRITE:
        return _has_grant(principal, grants, {AccessLevel.WRITE.value, AccessLevel.ADMIN.value})

    if action in {ResourceAction.DATASET_ADMIN, ResourceAction.PERMISSION_ADMIN, ResourceAction.ADMIN_OPERATE, ResourceAction.AUDIT_READ}:
        return _has_grant(principal, grants, {AccessLevel.ADMIN.value})

    return False


def enforce(principal: Principal, action: ResourceAction, context: ResourceContext) -> None:
    if not is_allowed(principal, action, context):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Principal '{principal.principal_id}' is not authorized for action '{action.value}'",
        )
