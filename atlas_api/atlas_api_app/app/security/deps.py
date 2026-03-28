from fastapi import Depends

from app.core.enums import DatasetVisibility, ResourceAction
from app.security.auth import resolve_principal
from app.security.models import Principal
from app.security.policy import ResourceContext, enforce


async def get_current_principal(principal: Principal = Depends(resolve_principal)) -> Principal:
    return principal


async def require_admin(principal: Principal = Depends(resolve_principal)) -> Principal:
    if not (principal.is_admin or principal.is_internal):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Admin role required")
    return principal


def authorize_public_dataset_read(principal: Principal, dataset_id: str) -> None:
    context = ResourceContext(resource_id=dataset_id, dataset_visibility=DatasetVisibility.PUBLIC, grants=[])
    enforce(principal, ResourceAction.DATASET_READ, context)
