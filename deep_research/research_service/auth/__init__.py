"""Authentication module for JWT token-based authentication."""

from research_service.auth.dependencies import get_current_user
from research_service.auth.jwt import create_access_token, decode_token, verify_token
from research_service.auth.schemas import APIKeyAuth, Token, TokenData

__all__ = [
    "APIKeyAuth",
    "Token",
    "TokenData",
    "create_access_token",
    "decode_token",
    "verify_token",
    "get_current_user",
]

