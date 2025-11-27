"""Application settings for the research service."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration values loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parent.parent.parent / ".env",
            Path(__file__).resolve().parent.parent.parent / ".env.local",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(
        default="Research Service",
        description="Human-readable service name used for metadata and docs.",
    )
    environment: Literal["local", "staging", "production"] = Field(
        default="local",
        alias="RESEARCH_SERVICE_ENV",
        description="High-level deployment environment used for logging decisions.",
    )

    http_host: str = Field(default="0.0.0.0", alias="RESEARCH_SERVICE_HTTP_HOST")
    http_port: int = Field(default=8081, alias="RESEARCH_SERVICE_HTTP_PORT")
    grpc_host: str = Field(default="0.0.0.0", alias="RESEARCH_SERVICE_GRPC_HOST")
    grpc_port: int = Field(default=50052, alias="RESEARCH_SERVICE_GRPC_PORT")
    enable_reload: bool = Field(default=True, alias="RESEARCH_SERVICE_RELOAD")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


settings = get_settings()

