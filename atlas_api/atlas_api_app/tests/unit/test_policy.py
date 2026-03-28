from app.core.enums import AccessLevel, DatasetVisibility, PrincipalType, ResourceAction
from app.security.models import Principal
from app.security.policy import PermissionGrant, ResourceContext, is_allowed


def test_public_dataset_read_allowed_without_grant() -> None:
    principal = Principal(principal_id="u1", principal_type=PrincipalType.USER, roles=set())
    context = ResourceContext(resource_id="ds1", dataset_visibility=DatasetVisibility.PUBLIC, grants=[])
    assert is_allowed(principal, ResourceAction.DATASET_READ, context) is True


def test_restricted_dataset_read_requires_grant() -> None:
    principal = Principal(principal_id="u1", principal_type=PrincipalType.USER, roles=set())
    context = ResourceContext(resource_id="ds1", dataset_visibility=DatasetVisibility.RESTRICTED, grants=[])
    assert is_allowed(principal, ResourceAction.DATASET_READ, context) is False

    granted = ResourceContext(
        resource_id="ds1",
        dataset_visibility=DatasetVisibility.RESTRICTED,
        grants=[PermissionGrant(principal_type="user", principal_id="u1", access_level=AccessLevel.READ.value)],
    )
    assert is_allowed(principal, ResourceAction.DATASET_READ, granted) is True
