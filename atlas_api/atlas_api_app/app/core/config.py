from __future__ import annotations

import logging
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_PLACEHOLDER_SECRETS = frozenset(
    {
        "",
        "change-me",
        "changeme",
        "secret",
        "test-internal-key",
        "local-dev-secret",
        "replace-me",
    }
)


class Settings(BaseSettings):
    app_name: str = Field(default="Veritas Atlas API", alias="ATLAS_APP_NAME")
    api_prefix: str = Field(default="/api/v1", alias="ATLAS_API_PREFIX")
    env: str = Field(default="dev", alias="ATLAS_ENV")

    auth_mode: str = Field(default="hybrid", alias="ATLAS_AUTH_MODE")
    internal_api_key: str = Field(default="test-internal-key", alias="ATLAS_INTERNAL_API_KEY")

    jwt_issuer: str = Field(default="https://issuer.example.com/", alias="ATLAS_JWT_ISSUER")
    jwt_audience: str = Field(default="veritas-atlas", alias="ATLAS_JWT_AUDIENCE")
    jwks_url: str = Field(default="https://issuer.example.com/.well-known/jwks.json", alias="ATLAS_JWKS_URL")
    dev_bearer_secret: str = Field(default="local-dev-secret", alias="ATLAS_DEV_BEARER_SECRET")

    # Phase 2: forwarded X-Principal-* headers (dev only by default; forbidden in production validation)
    allow_forwarded_principal: bool = Field(default=True, alias="ATLAS_ALLOW_FORWARDED_PRINCIPAL")

    database_url: str = Field(
        default="postgresql+psycopg2://atlas:atlas@127.0.0.1:5432/atlas_dev",
        alias="ATLAS_DATABASE_URL",
    )
    database_auto_create_schema: bool = Field(default=False, alias="ATLAS_DATABASE_AUTO_CREATE_SCHEMA")
    seed_demo_data_on_startup: bool = Field(default=True, alias="ATLAS_SEED_DEMO_DATA_ON_STARTUP")

    debug: bool = Field(default=False, alias="ATLAS_DEBUG")
    security_demo_enabled: bool = Field(default=True, alias="ATLAS_SECURITY_DEMO_ENABLED")

    pennsieve_api_token: str = Field(default="", alias="PENNSIEVE_API_TOKEN")
    pennsieve_api_secret: str = Field(default="", alias="PENNSIEVE_API_SECRET")
    pennsieve_organization_id: str = Field(default="", alias="PENNSIEVE_ORGANIZATION_ID")
    pennsieve_api_base_url: str = Field(default="https://api.pennsieve.io", alias="PENNSIEVE_API_BASE_URL")
    pennsieve_integration_enabled: bool = Field(default=False, alias="PENNSIEVE_INTEGRATION_ENABLED")
    pennsieve_request_timeout_seconds: float = Field(default=20.0, alias="PENNSIEVE_REQUEST_TIMEOUT_SECONDS")

    # Veritas integration (AtlasClient live mode)
    veritas_client_id: str = Field(default="veritas", alias="ATLAS_VERITAS_CLIENT_ID")
    veritas_client_secret: str = Field(default="", alias="ATLAS_VERITAS_CLIENT_SECRET")
    # When true in production, empty ATLAS_VERITAS_CLIENT_SECRET fails startup validation (strict Veritas integration).
    require_veritas_client_secret: bool = Field(default=False, alias="ATLAS_REQUIRE_VERITAS_CLIENT_SECRET")
    veritas_default_compute_target: str = Field(default="URMC_HPC", alias="ATLAS_VERITAS_DEFAULT_COMPUTE_TARGET")
    public_base_url: str = Field(default="http://127.0.0.1:8000", alias="ATLAS_PUBLIC_BASE_URL")

    staging_max_retries: int = Field(default=3, alias="ATLAS_STAGING_MAX_RETRIES")
    staging_retry_backoff_seconds: float = Field(default=1.0, alias="ATLAS_STAGING_RETRY_BACKOFF_SECONDS")
    metrics_enabled: bool = Field(default=True, alias="ATLAS_METRICS_ENABLED")

    # Operations: logging, CORS, optional in-process admin rate limit (single-worker)
    log_json: bool = Field(default=False, alias="ATLAS_LOG_JSON")
    log_level: str = Field(default="INFO", alias="ATLAS_LOG_LEVEL")
    cors_origins: str = Field(default="", alias="ATLAS_CORS_ORIGINS")
    admin_rate_limit_per_minute: int = Field(default=0, alias="ATLAS_ADMIN_RATE_LIMIT_PER_MINUTE")

    # Async jobs (Celery) + object storage (S3-compatible, e.g. MinIO) — optional; empty = disabled in /ready
    redis_url: str = Field(default="", alias="ATLAS_REDIS_URL")
    celery_broker_url: str = Field(default="", alias="ATLAS_CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="", alias="ATLAS_CELERY_RESULT_BACKEND")
    s3_endpoint_url: str = Field(default="", alias="ATLAS_S3_ENDPOINT_URL")
    s3_access_key: str = Field(default="", alias="ATLAS_S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="", alias="ATLAS_S3_SECRET_KEY")
    s3_bucket: str = Field(default="atlas", alias="ATLAS_S3_BUCKET")
    s3_region: str = Field(default="us-east-1", alias="ATLAS_S3_REGION")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def cors_origin_list(self) -> list[str]:
        if not (self.cors_origins or "").strip():
            return []
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def is_production(self) -> bool:
        return (self.env or "").strip().lower() == "production"

    @property
    def use_dev_jwt(self) -> bool:
        """HS256 dev tokens only when explicitly in dev-like env."""
        return (self.env or "").strip().lower() in {"dev", "development", "local"}

    @property
    def celery_effective_broker(self) -> str:
        return (self.celery_broker_url or self.redis_url or "memory://").strip()

    @property
    def celery_effective_backend(self) -> str:
        return (self.celery_result_backend or self.redis_url or "memory://").strip()

    @property
    def s3_configured(self) -> bool:
        return bool(
            (self.s3_endpoint_url or "").strip()
            and (self.s3_access_key or "").strip()
            and (self.s3_secret_key or "").strip()
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def validate_production_settings(settings: Settings) -> None:
    """Phase 1: fail fast when ATLAS_ENV=production and unsafe defaults remain."""
    if not settings.is_production:
        return

    problems: list[str] = []

    if settings.debug:
        problems.append("ATLAS_DEBUG must be false when ATLAS_ENV=production")

    if settings.database_url.strip().lower().startswith("sqlite"):
        problems.append("ATLAS_DATABASE_URL must not use SQLite when ATLAS_ENV=production")

    if settings.database_auto_create_schema:
        problems.append(
            "ATLAS_DATABASE_AUTO_CREATE_SCHEMA must be false in production; apply Alembic migrations before boot"
        )

    if settings.internal_api_key.strip().lower() in _PLACEHOLDER_SECRETS:
        problems.append("ATLAS_INTERNAL_API_KEY must be set to a strong non-placeholder value in production")

    if settings.dev_bearer_secret.strip().lower() in _PLACEHOLDER_SECRETS:
        problems.append("ATLAS_DEV_BEARER_SECRET must not be a placeholder in production (even if unused)")

    if settings.allow_forwarded_principal:
        problems.append(
            "ATLAS_ALLOW_FORWARDED_PRINCIPAL must be false in production (do not trust X-Principal-* from clients)"
        )

    if not settings.jwks_url.strip().startswith("https://"):
        problems.append("ATLAS_JWKS_URL must use https in production")

    if not settings.jwt_audience.strip():
        problems.append("ATLAS_JWT_AUDIENCE must be set to a non-empty audience string in production")
    iss = settings.jwt_issuer.strip().lower()
    if not settings.jwt_issuer.strip().startswith("https://"):
        problems.append("ATLAS_JWT_ISSUER should use an https issuer URL in production")
    elif "issuer.example.com" in iss:
        problems.append("ATLAS_JWT_ISSUER must be set to your real identity provider issuer URL in production")

    if settings.security_demo_enabled:
        problems.append("ATLAS_SECURITY_DEMO_ENABLED must be false in production")

    if settings.seed_demo_data_on_startup:
        problems.append("ATLAS_SEED_DEMO_DATA_ON_STARTUP must be false in production")

    origins = settings.cors_origin_list()
    if origins and any(o == "*" for o in origins):
        problems.append("ATLAS_CORS_ORIGINS must not use '*' in production; list explicit origins")

    if settings.pennsieve_integration_enabled:
        if settings.pennsieve_api_token.strip() in _PLACEHOLDER_SECRETS or not settings.pennsieve_api_token.strip():
            problems.append("PENNSIEVE_API_TOKEN must be set when PENNSIEVE_INTEGRATION_ENABLED=true in production")
        if not settings.pennsieve_organization_id.strip():
            problems.append("PENNSIEVE_ORGANIZATION_ID should be set when Pennsieve integration is enabled")

    if settings.require_veritas_client_secret and not (settings.veritas_client_secret or "").strip():
        problems.append(
            "ATLAS_VERITAS_CLIENT_SECRET must be set when ATLAS_REQUIRE_VERITAS_CLIENT_SECRET=true in production"
        )

    if problems:
        detail = "; ".join(problems)
        logger.error("Atlas API production configuration validation failed: %s", detail)
        raise RuntimeError(f"Invalid Atlas API production configuration: {detail}")
