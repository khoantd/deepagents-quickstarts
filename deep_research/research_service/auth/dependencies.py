"""FastAPI dependencies for authentication."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from research_service.auth.jwt import decode_token
from research_service.auth.schemas import TokenData

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    """Dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials from Authorization header

    Returns:
        TokenData with decoded token information

    Raises:
        HTTPException: If token is invalid, expired, or missing
    """
    token = credentials.credentials

    try:
        payload = decode_token(token)
        sub: str | None = payload.get("sub")
        exp: int | None = payload.get("exp")
        iat: int | None = payload.get("iat")

        if sub is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_data = TokenData(sub=sub, exp=exp, iat=iat)
        return token_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

