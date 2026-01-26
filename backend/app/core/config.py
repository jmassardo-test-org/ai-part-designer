"""
Application configuration settings.

Uses Pydantic Settings for environment variable management
with type validation and sensible defaults.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, computed_field
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
        return self.CORS_ORIGINS + [
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]
    
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
    STORAGE_ENDPOINT: str | None = "http://localhost:9000"
    STORAGE_ACCESS_KEY: str = "minioadmin"
    STORAGE_SECRET_KEY: str = "minioadmin"
    STORAGE_BUCKET_DESIGNS: str = "designs"
    STORAGE_BUCKET_EXPORTS: str = "exports"
    STORAGE_BUCKET_THUMBNAILS: str = "thumbnails"
    STORAGE_REGION: str = "us-east-1"
    
    # ===========================================
    # AI Provider Configuration
    # ===========================================
    # Provider: "openai", "ollama", "anthropic", or "azure"
    AI_PROVIDER: Literal["openai", "ollama", "anthropic", "azure"] = "openai"
    
    # OpenAI Settings
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 4096
    
    # Ollama Settings (for local development)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"  # or codellama, mistral, etc.
    
    # Anthropic Settings
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-3-sonnet-20240229"
    
    # Azure OpenAI Settings
    AZURE_OPENAI_API_KEY: str | None = None
    AZURE_OPENAI_ENDPOINT: str | None = None
    AZURE_OPENAI_DEPLOYMENT: str | None = None
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    
    # General AI Settings
    AI_MAX_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.3
    
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
    # Monitoring
    # ===========================================
    OTEL_EXPORTER_ENDPOINT: str | None = None
    SENTRY_DSN: str | None = None
    LOG_LEVEL: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Using lru_cache ensures settings are only loaded once.
    """
    return Settings()


# Global settings instance
settings = get_settings()
