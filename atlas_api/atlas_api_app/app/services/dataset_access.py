from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import DatasetVisibility, ResourceAction
from app.models.dataset import AtlasDataset
from app.models.dataset_grant import DatasetPermissionGrant
from app.security.models import Principal
from app.security.policy import PermissionGrant, ResourceContext, is_allowed


def _visibility(row: AtlasDataset) -> DatasetVisibility:
    try:
        return DatasetVisibility(row.visibility)
    except ValueError:
        return DatasetVisibility.PRIVATE


def load_grants_for_principal(db: Session, dataset_id: str, principal: Principal) -> list[PermissionGrant]:
    rows = db.scalars(
        select(DatasetPermissionGrant).where(
            DatasetPermissionGrant.dataset_id == dataset_id,
            DatasetPermissionGrant.principal_id == principal.principal_id,
            DatasetPermissionGrant.principal_type == principal.principal_type.value,
        )
    ).all()
    return [
        PermissionGrant(
            principal_type=r.principal_type,
            principal_id=r.principal_id,
            access_level=r.access_level,
        )
        for r in rows
    ]


def build_resource_context(row: AtlasDataset, grants: list[PermissionGrant]) -> ResourceContext:
    return ResourceContext(
        resource_id=row.dataset_id,
        dataset_visibility=_visibility(row),
        grants=grants,
    )


def principal_may_read_dataset(principal: Principal, row: AtlasDataset, db: Session) -> bool:
    grants = load_grants_for_principal(db, row.dataset_id, principal)
    ctx = build_resource_context(row, grants)
    return is_allowed(principal, ResourceAction.DATASET_READ, ctx)


def principal_may_create_staging(principal: Principal, row: AtlasDataset, db: Session) -> bool:
    grants = load_grants_for_principal(db, row.dataset_id, principal)
    ctx = build_resource_context(row, grants)
    return is_allowed(principal, ResourceAction.EXECUTION_CREATE, ctx)
