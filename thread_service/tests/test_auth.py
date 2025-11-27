"""Tests for authentication utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from thread_service.auth import (
    BCRYPT_MAX_PASSWORD_LENGTH,
    create_access_token,
    decode_access_token,
    generate_email_verification_token,
    generate_password_reset_token,
    get_token_expiry,
    hash_password,
    verify_password,
)
from thread_service.settings import get_settings

settings = get_settings()


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt hash format

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "testpassword123"
        hashed = hash_password(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_hash_password_truncates_long_passwords(self):
        """Test that passwords longer than 72 bytes are truncated."""
        # Create a password longer than 72 bytes
        long_password = "a" * 100
        hashed = hash_password(long_password)
        # Should still verify correctly (truncated version)
        assert verify_password(long_password, hashed) is True
        # The hash should be valid bcrypt format
        assert hashed.startswith("$2b$")

    def test_hash_password_unicode(self):
        """Test password hashing with unicode characters."""
        password = "测试密码123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"
        hashed1 = hash_password(password1)
        hashed2 = hash_password(password2)
        assert hashed1 != hashed2

    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "testpassword"
        hashed1 = hash_password(password)
        hashed2 = hash_password(password)
        # Hashes should be different due to salt
        assert hashed1 != hashed2
        # But both should verify correctly
        assert verify_password(password, hashed1) is True
        assert verify_password(password, hashed2) is True


class TestJWTTokens:
    """Test JWT token creation and decoding."""

    def test_create_access_token(self):
        """Test JWT token creation."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_decode_access_token_valid(self):
        """Test decoding a valid JWT token."""
        data = {"sub": "user123", "email": "test@example.com"}
        token = create_access_token(data)
        decoded = decode_access_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user123"
        assert decoded["email"] == "test@example.com"
        assert "exp" in decoded
        assert "iat" in decoded

    def test_decode_access_token_invalid_signature(self):
        """Test decoding a token with invalid signature."""
        # Create a token with wrong secret
        data = {"sub": "user123", "email": "test@example.com"}
        token = jwt.encode(data, "wrong-secret", algorithm="HS256")
        decoded = decode_access_token(token)
        assert decoded is None

    def test_decode_access_token_expired(self):
        """Test decoding an expired token."""
        data = {"sub": "user123", "email": "test@example.com"}
        # Create token with past expiration
        expire = datetime.now(timezone.utc) - timedelta(hours=1)
        data["exp"] = expire
        data["iat"] = datetime.now(timezone.utc) - timedelta(hours=2)
        token = jwt.encode(data, settings.jwt_secret, algorithm="HS256")
        decoded = decode_access_token(token)
        assert decoded is None

    def test_decode_access_token_malformed(self):
        """Test decoding a malformed token."""
        decoded = decode_access_token("not.a.valid.token")
        assert decoded is None

    def test_decode_access_token_empty(self):
        """Test decoding an empty token."""
        decoded = decode_access_token("")
        assert decoded is None

    def test_create_access_token_with_expires_delta(self):
        """Test creating token with custom expiration."""
        data = {"sub": "user123", "email": "test@example.com"}
        expires_delta = timedelta(hours=1)
        token = create_access_token(data, expires_delta=expires_delta)
        decoded = decode_access_token(token)
        assert decoded is not None
        # Check expiration is approximately 1 hour from now
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        expected_exp = now + expires_delta
        # Allow 5 second tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 5


class TestTokenGeneration:
    """Test token generation utilities."""

    def test_generate_email_verification_token(self):
        """Test email verification token generation."""
        token = generate_email_verification_token()
        assert isinstance(token, str)
        assert len(token) > 0
        # Should be URL-safe base64
        assert " " not in token
        assert "\n" not in token

    def test_generate_email_verification_token_unique(self):
        """Test that generated tokens are unique."""
        token1 = generate_email_verification_token()
        token2 = generate_email_verification_token()
        assert token1 != token2

    def test_generate_password_reset_token(self):
        """Test password reset token generation."""
        token = generate_password_reset_token()
        assert isinstance(token, str)
        assert len(token) > 0
        # Should be URL-safe base64
        assert " " not in token
        assert "\n" not in token

    def test_generate_password_reset_token_unique(self):
        """Test that generated tokens are unique."""
        token1 = generate_password_reset_token()
        token2 = generate_password_reset_token()
        assert token1 != token2

    def test_get_token_expiry_default(self):
        """Test token expiry calculation with default (24 hours)."""
        expiry = get_token_expiry()
        now = datetime.now(timezone.utc)
        expected = now + timedelta(hours=24)
        # Allow 1 second tolerance
        assert abs((expiry - expected).total_seconds()) < 1

    def test_get_token_expiry_custom(self):
        """Test token expiry calculation with custom hours."""
        expiry = get_token_expiry(hours=48)
        now = datetime.now(timezone.utc)
        expected = now + timedelta(hours=48)
        # Allow 1 second tolerance
        assert abs((expiry - expected).total_seconds()) < 1

    def test_get_token_expiry_timezone(self):
        """Test that token expiry is in UTC."""
        expiry = get_token_expiry()
        assert expiry.tzinfo == timezone.utc

