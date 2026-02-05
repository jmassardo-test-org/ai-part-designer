"""
Application configuration settings.

Uses Pydantic Settings for environment variable management
with type validation and sensible defaults.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ===========================================
    # Application Settings
    # ===========================================
    APP_NAME: str = "AssemblematicAI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    TESTING: bool = False
    ENVIRONMENT: Literal["development", "staging", "production", "test"] = "development"

    # API Settings
    API_V1_PREFIX: str = "/api/v1"

    # ===========================================
    # Security
    # ===========================================
    SECRET_KEY: str = Field(
        default="CHANGE-THIS-IN-PRODUCTION-USE-STRONG-KEY",
        description="Secret key for JWT signing and encryption",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Short-lived for security
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Password requirements
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_MAX_LENGTH: int = 128
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True

    # Account security
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15
    REQUIRE_EMAIL_VERIFICATION: bool = True

    # Session security
    SESSION_TIMEOUT_MINUTES: int = 60
    CONCURRENT_SESSION_LIMIT: int = 5  # Max active sessions per user

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    CORS_ALLOW_CREDENTIALS: bool = True

    # HTTPS/TLS
    FORCE_HTTPS: bool = Field(
        default=False,
        description="Force HTTPS in production",
    )

    @computed_field
    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        """Get allowed CORS origins based on environment."""
        if self.ENVIRONMENT == "production":
            # In production, should be set explicitly
            return self.CORS_ORIGINS
        # In development, allow localhost variations
        return [*self.CORS_ORIGINS, "http://127.0.0.1:3000", "http://127.0.0.1:5173"]

    # ===========================================
    # Database
    # ===========================================
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "ai_part_designer"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """Construct async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Construct sync PostgreSQL connection URL (for Alembic)."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ===========================================
    # Redis
    # ===========================================
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_DB: int = 0

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        """Construct Redis connection URL."""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ===========================================
    # Object Storage (S3-compatible)
    # ===========================================
    STORAGE_BACKEND: Literal["s3", "gcs", "azure", "minio"] = "minio"
    # Support both STORAGE_ENDPOINT and S3_ENDPOINT_URL for docker-compose compatibility
    STORAGE_ENDPOINT: str | None = None
    S3_ENDPOINT_URL: str | None = "http://localhost:9000"
    STORAGE_ACCESS_KEY: str | None = None
    AWS_ACCESS_KEY_ID: str = "minioadmin"
    STORAGE_SECRET_KEY: str | None = None
    AWS_SECRET_ACCESS_KEY: str = "minioadmin"
    STORAGE_BUCKET_DESIGNS: str = "designs"
    STORAGE_BUCKET_EXPORTS: str = "exports"
    STORAGE_BUCKET_THUMBNAILS: str = "thumbnails"
    STORAGE_REGION: str | None = None
    AWS_REGION: str = "us-east-1"

    @property
    def storage_endpoint(self) -> str:
        """Get storage endpoint, supporting both env var names."""
        return self.STORAGE_ENDPOINT or self.S3_ENDPOINT_URL or "http://localhost:9000"

    @property
    def storage_access_key(self) -> str:
        """Get storage access key, supporting both env var names."""
        return self.STORAGE_ACCESS_KEY or self.AWS_ACCESS_KEY_ID

    @property
    def storage_secret_key(self) -> str:
        """Get storage secret key, supporting both env var names."""
        return self.STORAGE_SECRET_KEY or self.AWS_SECRET_ACCESS_KEY

    @property
    def storage_region(self) -> str:
        """Get storage region, supporting both env var names."""
        return self.STORAGE_REGION or self.AWS_REGION

    # ===========================================
    # AI Provider Configuration
    # ===========================================
    # Provider: "anthropic" (Claude is the primary and only supported provider)
    AI_PROVIDER: Literal["anthropic"] = "anthropic"

    # Anthropic Claude Settings (primary provider)
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # General AI Settings
    AI_MAX_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.3

    # ===========================================
    # OAuth Providers
    # ===========================================
    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    # GitHub OAuth
    GITHUB_CLIENT_ID: str | None = None
    GITHUB_CLIENT_SECRET: str | None = None

    # OAuth callback base URL (frontend URL)
    OAUTH_REDIRECT_BASE: str = "http://localhost:5173"

    # Frontend URL for redirects and email links
    # In production: https://assemblematic.ai
    FRONTEND_URL: str = "http://localhost:5173"

    # ===========================================
    # Rate Limiting
    # ===========================================
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    # ===========================================
    # Job Processing
    # ===========================================
    CAD_WORKER_TIMEOUT: int = 300  # seconds
    MAX_CONCURRENT_JOBS: int = 10
    JOB_RETRY_DELAY: int = 60  # seconds

    # ===========================================
    # File Storage (Local)
    # ===========================================
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ===========================================
    # Payment Processing (Stripe)
    # ===========================================
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_PUBLISHABLE_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None

    # Stripe Price IDs (set in Stripe Dashboard)
    STRIPE_PRICE_ID_PRO_MONTHLY: str | None = None
    STRIPE_PRICE_ID_PRO_YEARLY: str | None = None
    STRIPE_PRICE_ID_ENTERPRISE_MONTHLY: str | None = None
    STRIPE_PRICE_ID_ENTERPRISE_YEARLY: str | None = None

    # ===========================================
    # Monitoring
    # ===========================================
    OTEL_EXPORTER_ENDPOINT: str | None = None
    SENTRY_DSN: str | None = None
    LOG_LEVEL: str = "INFO"

    # ===========================================
    # CAD System v2 Feature Flags
    # ===========================================
    # Enable CAD v2 system (declarative schema + Build123d)
    CAD_V2_ENABLED: bool = Field(
        default=True,
        description="Enable CAD v2 API endpoints (/api/v2/). "
        "When True, v2 endpoints are available alongside v1.",
    )

    # Use CAD v2 as default for legacy v1 endpoints
    CAD_V2_AS_DEFAULT: bool = Field(
        default=True,
        description="Route v1 CAD generation requests through v2 pipeline. "
        "Requires CAD_V2_ENABLED=True. Enables gradual migration.",
    )

    # Add deprecation headers to v1 API responses
    CAD_V1_DEPRECATION_HEADERS: bool = Field(
        default=True,
        description="Add Deprecation and Sunset headers to v1 CAD API responses. "
        "Warns clients to migrate to v2.",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Using lru_cache ensures settings are only loaded once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
