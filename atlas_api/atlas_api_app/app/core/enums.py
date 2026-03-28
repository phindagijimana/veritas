from enum import Enum


class DatasetVisibility(str, Enum):
    PUBLIC = "public"
    RESTRICTED = "restricted"
    PRIVATE = "private"


class DatasetAccessClass(str, Enum):
    TRAINING = "training"
    VALIDATION = "validation"
    INTERNAL = "internal"


class StorageProvider(str, Enum):
    """Where the canonical dataset bytes live or are first resolved."""

    PENNSIEVE = "pennsieve"
    URMC_HPC = "urmc_hpc"
    # Out-of-domain / institution HPC (e.g. national OOD facility); staging still uses allowed_compute_targets.
    OOD_HPC = "ood_hpc"


class PrincipalType(str, Enum):
    USER = "user"
    SERVICE = "service"
    GROUP = "group"
    INTERNAL = "internal"


class AccessLevel(str, Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class ResourceAction(str, Enum):
    DATASET_READ = "dataset:read"
    DATASET_WRITE = "dataset:write"
    DATASET_ADMIN = "dataset:admin"
    EXECUTION_CREATE = "execution:create"
    AUDIT_READ = "audit:read"
    PERMISSION_ADMIN = "permission:admin"
    ADMIN_OPERATE = "admin:operate"
