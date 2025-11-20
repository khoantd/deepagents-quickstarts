"""Application settings for the thread persistence service."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration values loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parent.parent / ".env",
            Path(__file__).resolve().parent.parent / ".env.local",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(
        default="Thread Service",
        description="Human-readable service name used for metadata and docs.",
    )
    environment: Literal["local", "staging", "production"] = Field(
        default="local",
        alias="THREAD_SERVICE_ENV",
        description="High-level deployment environment used for logging decisions.",
    )

    http_host: str = Field(default="0.0.0.0", alias="THREAD_SERVICE_HTTP_HOST")
    http_port: int = Field(default=8080, alias="THREAD_SERVICE_HTTP_PORT")
    grpc_host: str = Field(default="0.0.0.0", alias="THREAD_SERVICE_GRPC_HOST")
    grpc_port: int = Field(default=50051, alias="THREAD_SERVICE_GRPC_PORT")
    enable_reload: bool = Field(default=True, alias="THREAD_SERVICE_RELOAD")

    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", alias="POSTGRES_PASSWORD")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="thread_service", alias="POSTGRES_DB")

    jwt_secret: str = Field(
        default="change-me-in-production",
        alias="JWT_SECRET",
        description="Secret key for JWT token signing",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=10080, alias="JWT_EXPIRE_MINUTES")  # 7 days

    oauth_google_client_id: str | None = Field(default=None, alias="OAUTH_GOOGLE_CLIENT_ID")
    oauth_google_client_secret: str | None = Field(default=None, alias="OAUTH_GOOGLE_CLIENT_SECRET")
    oauth_github_client_id: str | None = Field(default=None, alias="OAUTH_GITHUB_CLIENT_ID")
    oauth_github_client_secret: str | None = Field(default=None, alias="OAUTH_GITHUB_CLIENT_SECRET")

    frontend_url: str = Field(
        default="http://localhost:3000",
        alias="FRONTEND_URL",
        description="Frontend URL for OAuth callbacks",
    )

    smtp_host: str | None = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str | None = Field(default=None, alias="SMTP_USER")
    smtp_password: str | None = Field(default=None, alias="SMTP_PASSWORD")
    smtp_from_email: str | None = Field(default=None, alias="SMTP_FROM_EMAIL")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")

    @property
    def database_url(self) -> str:
        """Return the SQLAlchemy async database URL."""

        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


settings = get_settings()
