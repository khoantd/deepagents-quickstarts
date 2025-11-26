"""Authentication utilities for password hashing, JWT tokens, and token generation."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from .settings import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt has a maximum password length of 72 bytes
BCRYPT_MAX_PASSWORD_LENGTH = 72

# JWT settings
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


def _truncate_password(password: str) -> str:
    """Truncate password to bcrypt's 72-byte limit.

    Args:
        password: Plain text password

    Returns:
        Truncated password (max 72 bytes)
    """
    # Encode to bytes, truncate, and decode back
    # Use errors='ignore' to avoid issues with multi-byte chars at boundary
    return password.encode("utf-8")[:BCRYPT_MAX_PASSWORD_LENGTH].decode("utf-8", errors="ignore")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    return pwd_context.hash(_truncate_password(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(_truncate_password(plain_password), hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Args:
        data: Data to encode in the token (typically user_id and email)
        expires_delta: Optional expiration time delta. Defaults to 7 days.

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.jwt_secret, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a JWT access token.

    Args:
        token: JWT token string to decode

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_email_verification_token() -> str:
    """Generate a secure random token for email verification.

    Returns:
        Random token string
    """
    return secrets.token_urlsafe(32)


def generate_password_reset_token() -> str:
    """Generate a secure random token for password reset.

    Returns:
        Random token string
    """
    return secrets.token_urlsafe(32)


def get_token_expiry(hours: int = 24) -> datetime:
    """Get a token expiry datetime.

    Args:
        hours: Number of hours until expiry (default: 24)

    Returns:
        Datetime object representing expiry time
    """
    return datetime.now(timezone.utc) + timedelta(hours=hours)

