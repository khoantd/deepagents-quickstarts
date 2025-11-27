"""Application settings for the research service."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, computed_field
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

    # LiteLLM Proxy Configuration
    litellm_api_base: str | None = Field(
        default=None,
        alias="LITELLM_API_BASE",
        description="Base URL for LiteLLM proxy server (e.g., http://localhost:4000)",
    )
    litellm_api_key: str | None = Field(
        default=None,
        alias="LITELLM_API_KEY",
        description="API key for LiteLLM proxy authentication",
    )
    litellm_model: str | None = Field(
        default=None,
        alias="LITELLM_MODEL",
        description="Model name to use via LiteLLM proxy (e.g., gpt-4o, claude-sonnet-4-5-20250929)",
    )

    # JWT Authentication Configuration
    jwt_secret_key: str = Field(
        ...,
        alias="JWT_SECRET_KEY",
        description="Secret key for signing JWT tokens (required)",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        alias="JWT_ALGORITHM",
        description="JWT signing algorithm (default: HS256)",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=30,
        alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        description="JWT access token expiration time in minutes (default: 30)",
    )
    jwt_issuer: str | None = Field(
        default=None,
        alias="JWT_ISSUER",
        description="Optional issuer claim for JWT tokens",
    )

    # API Key Configuration (stored as string, accessed as list via computed field)
    api_keys_str: str | None = Field(
        default=None,
        alias="API_KEYS",
        description="Comma-separated list of valid API keys for authentication",
        exclude=True,  # Exclude from serialization, use computed field instead
    )

    @computed_field
    @property
    def api_keys(self) -> list[str]:
        """Parse comma-separated API keys string into list."""
        if self.api_keys_str is None or not self.api_keys_str.strip():
            return []
        return [key.strip() for key in self.api_keys_str.split(",") if key.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""

    return Settings()


settings = get_settings()

