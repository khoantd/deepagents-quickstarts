"""Pydantic schemas for authentication requests and responses."""

from __future__ import annotations

from pydantic import BaseModel, Field


class APIKeyAuth(BaseModel):
    """Request schema for API key authentication."""

    api_key: str = Field(..., description="API key for authentication")


class Token(BaseModel):
    """Response schema for JWT token."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")


class TokenData(BaseModel):
    """Schema for decoded token data."""

    sub: str | None = Field(default=None, description="Subject (user identifier)")
    exp: int | None = Field(default=None, description="Expiration timestamp")
    iat: int | None = Field(default=None, description="Issued at timestamp")

