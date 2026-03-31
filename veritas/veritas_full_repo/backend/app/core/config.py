from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Dev UI is often opened as either hostname; both must be allowed for browser CORS.
_DEFAULT_DEV_UI_ORIGINS = ("http://localhost:7000", "http://127.0.0.1:7000")

_PLACEHOLDER_SECRETS = frozenset(
    {
        "",
        "change-me",
        "changeme",
        "secret",
        "replace-me",
        "replace-with-openssl-rand-hex-32",
        "replace-with-staging-only-secret",
        "replace-with-atlas-issued-secret",
    }
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Core API ---
    app_name: str = "Veritas API"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://veritas:veritas@127.0.0.1:5433/veritas_dev"
    # When false, schema must exist (run `alembic upgrade head`). Required false in production.
    database_auto_create_schema: bool = False
    # Demo datasets/requests/HPC seed in main.seed_data(). Never use in production.
    seed_demo_data_on_startup: bool = True
    redis_url: str = "redis://127.0.0.1:6380/0"
    # When true, /ready pings Redis and POST /jobs/monitor/sweep enqueues Celery work instead of running inline.
    job_queue_enabled: bool = False
    # Celery queue name (legacy env name RQ_QUEUE_NAME retained for existing deployments)
    rq_queue_name: str = "ai-biomarkers"
    rq_job_timeout_seconds: int = 3600
    rq_retry_max: int = 2
    rq_retry_intervals: str = "30,120,300"
    rq_failed_job_ttl_seconds: int = 604800

    allowed_origins: list[str] = Field(default_factory=lambda: list(_DEFAULT_DEV_UI_ORIGINS))
    # Comma-separated hostnames for TrustedHostMiddleware (e.g. api.veritas.example.com,localhost). Empty = disabled.
    trusted_hosts: str = ""

    # --- HPC / Slurm ---
    hpc_mode: Literal["mock", "slurm"] = "mock"
    # If true, API startup verifies an active HPC row and SSH reachability (Slurm mode only).
    hpc_validate_on_startup: bool = False
    # Shell lines inserted into generated sbatch after headers (e.g. `module load apptainer`).
    hpc_job_prologue_sh: str = ""
    ssh_connect_timeout_seconds: int = 8
    ssh_strict_host_key_checking: bool = False
    slurm_remote_workdir: str = "~/veritas/jobs"
    slurm_poll_command: str = "squeue -h -j {job_id} -o %T"
    slurm_cancel_command: str = "scancel {job_id}"
    scheduler_sync_enabled: bool = True
    runtime_engine: str = "docker"
    job_monitor_interval_seconds: int = 30

    # --- Artifacts & datasets ---
    artifact_root_dir: str = "./var/veritas_artifacts"
    public_artifact_base_url: str = "http://localhost:6000/static"
    storage_backend: Literal["local", "s3"] = "local"
    s3_endpoint_url: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_bucket: str = "veritas"
    s3_region: str = "us-east-1"
    dataset_root_dir: str = "./sample_data"
    prometheus_enabled: bool = True

    @property
    def s3_configured(self) -> bool:
        return self.storage_backend == "s3" and bool(
            (self.s3_endpoint_url or "").strip()
            and (self.s3_access_key or "").strip()
            and (self.s3_secret_key or "").strip()
        )

    # --- Pipeline images ---
    image_validation_mode: str = "local"
    image_validation_timeout_seconds: int = 60

    # --- Auth ---
    auth_enabled: bool = False
    auth_mode: str = "local"
    auth_secret_key: str = "change-me"
    auth_algorithm: str = "HS256"
    auth_access_token_expire_minutes: int = 60
    auth_default_dev_email: str = "dev@veritas.local"
    auth_default_dev_role: str = "admin"

    # --- Atlas / Pennsieve ---
    atlas_api_base_url: str = "https://atlas.example.org/api/v1"
    atlas_api_client_id: str = "veritas"
    atlas_api_client_secret: str = "change-me"
    atlas_api_timeout_seconds: int = 20
    atlas_dataset_mode: str = "atlas"
    pennsieve_base_url: str = "https://api.pennsieve.io"
    pennsieve_timeout_seconds: int = 30
    dataset_staging_root: str = "/scratch/veritas/staging"
    # MELD Graph pipeline jobs (runtime_profile=meld_graph): host dir with license.txt + meld_license.txt
    meld_license_host_dir: str = ""
    # Used when staged_dataset_path is omitted and VERITAS_STAGED_DATASET_PATH is unset (e.g. IDEAS OOD mirror)
    meld_ideas_default_staging_path: str = "/ood/share/datasets/ideas"
    atlas_stage_script_name: str = "stage_dataset.sh"
    atlas_stage_env_filename: str = "atlas_stage.env"
    atlas_monitor_poll_seconds: int = 30
    # mock: no outbound Atlas HTTP (in-process fixtures). live: AtlasClient calls atlas_api_base_url.
    atlas_integration_mode: Literal["mock", "live"] = "mock"
    # Optional bearer for Pennsieve manifest fetch when atlas_integration_mode=live.
    pennsieve_api_token: str = ""
    # Path appended to pennsieve_base_url; {dataset_id} substituted (e.g. /datasets/{dataset_id}/manifest).
    pennsieve_manifest_path_template: str = "/datasets/{dataset_id}/manifest"

    # --- HTTP hardening (Phase 8) ---
    # 0 disables the Content-Length check (not recommended for production).
    max_request_body_bytes: int = 52428800
    # Trust X-Forwarded-For when behind a reverse proxy (rate limiting client IP).
    rate_limit_trust_proxy_headers: bool = False
    # limits.parse() strings, e.g. "30/minute". Empty = no extra limit (global SlowAPI still applies).
    auth_login_rate_limit: str = "30/minute"
    auth_register_rate_limit: str = "15/hour"

    @field_validator("auth_login_rate_limit", "auth_register_rate_limit", mode="before")
    @classmethod
    def strip_auth_rate_limit_strings(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        if v is None or v == "":
            return list(_DEFAULT_DEV_UI_ORIGINS)
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        if isinstance(v, str):
            return [part.strip() for part in v.split(",") if part.strip()]
        raise TypeError("allowed_origins must be a comma-separated string or a list of strings")

    @model_validator(mode="after")
    def normalize_public_urls(self) -> Settings:
        if self.public_artifact_base_url:
            self.public_artifact_base_url = self.public_artifact_base_url.rstrip("/")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def trusted_hosts_list(settings: Settings) -> list[str] | None:
    raw = (settings.trusted_hosts or "").strip()
    if not raw:
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


def validate_production_settings(settings: Settings) -> None:
    """
    Fail fast when APP_ENV=production and unsafe defaults are still in place.
    Call from application lifespan (and optionally worker entrypoints).
    """
    if (settings.app_env or "").strip().lower() != "production":
        return

    problems: list[str] = []

    if settings.debug:
        problems.append("DEBUG must be false when APP_ENV=production")

    if settings.database_url.strip().lower().startswith("sqlite"):
        problems.append("DATABASE_URL must not use SQLite when APP_ENV=production")

    if settings.database_auto_create_schema:
        problems.append(
            "DATABASE_AUTO_CREATE_SCHEMA must be false when APP_ENV=production; apply schema with Alembic "
            "(`alembic upgrade head`) before boot"
        )

    if settings.seed_demo_data_on_startup:
        problems.append("SEED_DEMO_DATA_ON_STARTUP must be false when APP_ENV=production")

    if settings.hpc_mode == "slurm" and not settings.ssh_strict_host_key_checking:
        problems.append(
            "SSH_STRICT_HOST_KEY_CHECKING must be true when APP_ENV=production and HPC_MODE=slurm "
            "(or use a bastion/jump host with known host keys)"
        )

    if settings.auth_enabled and settings.auth_secret_key.strip().lower() in _PLACEHOLDER_SECRETS:
        problems.append("AUTH_SECRET_KEY must be set to a strong, non-placeholder value when AUTH_ENABLED=true in production")

    if settings.atlas_api_client_secret.strip().lower() in _PLACEHOLDER_SECRETS:
        problems.append(
            "ATLAS_API_CLIENT_SECRET must be set to a real credential (not a placeholder) when APP_ENV=production"
        )

    if settings.atlas_integration_mode == "live":
        url = (settings.atlas_api_base_url or "").strip().lower()
        if "example.org" in url or "atlas.example" in url:
            problems.append(
                "ATLAS_API_BASE_URL must point to a real Atlas when ATLAS_INTEGRATION_MODE=live in production "
                "(replace atlas.example.org / example.org with your deployment URL)"
            )

    for origin in settings.allowed_origins:
        if (origin or "").strip() == "*":
            problems.append("ALLOWED_ORIGINS must not be '*' in production; list explicit HTTPS origins")

    if problems:
        detail = "; ".join(problems)
        logger.error("Production configuration validation failed: %s", detail)
        raise RuntimeError(f"Invalid production configuration: {detail}")


