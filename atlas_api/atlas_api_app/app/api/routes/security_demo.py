from fastapi import APIRouter, Depends

from app.security.deps import get_current_principal, require_admin, authorize_public_dataset_read
from app.security.models import Principal

router = APIRouter(prefix="/security-demo", tags=["security-demo"])


@router.get("/me")
async def who_am_i(principal: Principal = Depends(get_current_principal)) -> dict:
    return {
        "principal_id": principal.principal_id,
        "principal_type": principal.principal_type.value,
        "roles": sorted(principal.roles),
        "auth_source": principal.auth_source,
    }


@router.get("/datasets/{dataset_id}")
async def read_dataset(dataset_id: str, principal: Principal = Depends(get_current_principal)) -> dict:
    authorize_public_dataset_read(principal, dataset_id)
    return {"dataset_id": dataset_id, "access": "granted", "scope": "public-demo"}


@router.get("/admin")
async def admin_only(principal: Principal = Depends(require_admin)) -> dict:
    return {"ok": True, "principal_id": principal.principal_id}
