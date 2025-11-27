"""Tests for authentication middleware."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from thread_service.auth import create_access_token, decode_access_token
from thread_service.middleware import get_current_user, get_current_user_optional
from thread_service.models import User


class TestGetCurrentUser:
    """Test get_current_user middleware."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, test_user, test_session):
        """Test getting current user with valid token."""
        token = create_access_token(data={"sub": str(test_user.id), "email": test_user.email})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user(credentials, test_session)
        assert user.id == test_user.id
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self, test_session):
        """Test getting current user with invalid token."""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token(self, test_session):
        """Test getting current user with expired token."""
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        from thread_service.settings import get_settings

        settings = get_settings()
        # Create expired token
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": str(uuid4()),
            "email": "test@example.com",
            "exp": expire,
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_current_user_missing_sub(self, test_session):
        """Test getting current user with token missing sub."""
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        from thread_service.settings import get_settings

        settings = get_settings()
        payload = {
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token payload" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_user_id(self, test_session):
        """Test getting current user with invalid user ID in token."""
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        from thread_service.settings import get_settings

        settings = get_settings()
        payload = {
            "sub": "not-a-uuid",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid user ID" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, test_session):
        """Test getting current user when user doesn't exist."""
        non_existent_id = uuid4()
        token = create_access_token(data={"sub": str(non_existent_id), "email": "nonexistent@example.com"})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials, test_session)
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found" in exc_info.value.detail


class TestGetCurrentUserOptional:
    """Test get_current_user_optional middleware."""

    @pytest.mark.asyncio
    async def test_get_current_user_optional_with_token(self, test_user, test_session):
        """Test getting current user optional with valid token."""
        token = create_access_token(data={"sub": str(test_user.id), "email": test_user.email})
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user_optional(credentials, test_session)
        assert user is not None
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_current_user_optional_without_token(self, test_session):
        """Test getting current user optional without token."""
        user = await get_current_user_optional(None, test_session)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_invalid_token(self, test_session):
        """Test getting current user optional with invalid token."""
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_token")
        user = await get_current_user_optional(credentials, test_session)
        assert user is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_expired_token(self, test_session):
        """Test getting current user optional with expired token."""
        from datetime import datetime, timedelta, timezone

        from jose import jwt

        from thread_service.settings import get_settings

        settings = get_settings()
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": str(uuid4()),
            "email": "test@example.com",
            "exp": expire,
            "iat": datetime.now(timezone.utc) - timedelta(hours=2),
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        user = await get_current_user_optional(credentials, test_session)
        assert user is None

