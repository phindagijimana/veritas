from dataclasses import dataclass, field
from typing import Any
from app.core.enums import PrincipalType


@dataclass
class Principal:
    principal_id: str
    principal_type: PrincipalType
    roles: set[str] = field(default_factory=set)
    claims: dict[str, Any] = field(default_factory=dict)
    auth_source: str = "anonymous"

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles

    @property
    def is_internal(self) -> bool:
        return self.principal_type == PrincipalType.INTERNAL
