"""Authentication router for JWT token generation."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from research_service.auth import create_access_token, verify_token
from research_service.auth.schemas import APIKeyAuth, Token
from research_service.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

security = HTTPBearer()


@router.post(
    "/token",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Get JWT Token",
    response_description="JWT access token for API authentication",
)
async def get_token(request: APIKeyAuth) -> Token:
    """Authenticate with API key and receive JWT access token.

    Args:
        request: API key authentication request

    Returns:
        Token response with access token and metadata

    Raises:
        HTTPException: If API key is invalid
    """
    settings = get_settings()

    # Validate API key
    if not settings.api_keys:
        logger.warning("No API keys configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured",
        )

    if request.api_key not in settings.api_keys:
        logger.warning("Invalid API key attempted")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token(data={"sub": request.api_key})
    expires_in = settings.jwt_access_token_expire_minutes * 60

    return Token(access_token=access_token, token_type="bearer", expires_in=expires_in)


@router.post(
    "/verify",
    status_code=status.HTTP_200_OK,
    summary="Verify JWT Token",
    response_description="Token verification result",
)
async def verify_token_endpoint(
    credentials: HTTPAuthorizationCredentials = security,
) -> dict[str, bool]:
    """Verify if a JWT token is valid.

    Args:
        credentials: HTTP Bearer token credentials from Authorization header

    Returns:
        Dictionary with verification result

    Raises:
        HTTPException: If token is invalid
    """
    token = credentials.credentials
    is_valid = verify_token(token)

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"valid": True}

