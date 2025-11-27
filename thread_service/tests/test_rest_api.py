"""Tests for REST API endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import status

from thread_service.models import AttachmentKind, MessageKind, ParticipantRole, ThreadStatus


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/healthz")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestThreadEndpoints:
    """Test thread CRUD endpoints."""

    def test_create_thread_minimal(self, authenticated_client, test_user):
        """Test creating thread with minimal fields."""
        response = authenticated_client.post(
            "/threads",
            json={"title": "New Thread"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == "New Thread"
        assert data["status"] == "open"
        assert data["summary"] is None
        assert data["metadata"] == {}
        assert data["participants"] == []
        assert data["messages"] == []

    def test_create_thread_with_participants(self, authenticated_client, test_user):
        """Test creating thread with participants."""
        response = authenticated_client.post(
            "/threads",
            json={
                "title": "Thread with Participants",
                "participants": [
                    {"role": "user", "display_name": "User 1"},
                    {"role": "agent", "display_name": "Agent 1"},
                ],
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["participants"]) == 2
        assert data["participants"][0]["role"] == "user"
        assert data["participants"][1]["role"] == "agent"

    def test_create_thread_with_metadata(self, authenticated_client, test_user):
        """Test creating thread with metadata."""
        metadata = {"key": "value", "number": 123}
        response = authenticated_client.post(
            "/threads",
            json={"title": "Thread with Metadata", "metadata": metadata},
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["metadata"] == metadata

    def test_create_thread_unauthorized(self, client):
        """Test creating thread without authentication."""
        response = client.post(
            "/threads",
            json={"title": "New Thread"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_threads_default(self, authenticated_client, test_user, test_thread):
        """Test listing threads with default pagination."""
        response = authenticated_client.get("/threads")
        assert response.status_code == 200
        data = response.json()
        assert "threads" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["threads"]) > 0

    def test_list_threads_pagination(self, authenticated_client, test_user, multiple_threads):
        """Test listing threads with pagination."""
        response = authenticated_client.get("/threads?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["threads"]) == 2
        assert data["total"] == 5

        response = authenticated_client.get("/threads?limit=2&offset=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["threads"]) == 2

    def test_list_threads_status_filter(self, authenticated_client, test_user, multiple_threads):
        """Test listing threads with status filter."""
        response = authenticated_client.get("/threads?status=open")
        assert response.status_code == 200
        data = response.json()
        assert all(thread["status"] == "open" for thread in data["threads"])

    def test_list_threads_user_isolation(self, authenticated_client, test_user2, test_thread2):
        """Test that users only see their own threads."""
        response = authenticated_client.get("/threads")
        assert response.status_code == 200
        data = response.json()
        # Should not see test_thread2 which belongs to test_user2
        thread_ids = [t["id"] for t in data["threads"]]
        assert str(test_thread2.id) not in thread_ids

    def test_get_thread_success(self, authenticated_client, test_user, test_thread):
        """Test getting a thread by ID."""
        response = authenticated_client.get(f"/threads/{test_thread.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_thread.id)
        assert data["title"] == test_thread.title
        assert len(data["participants"]) > 0
        assert len(data["messages"]) > 0

    def test_get_thread_not_found(self, authenticated_client, test_user):
        """Test getting non-existent thread."""
        response = authenticated_client.get(f"/threads/{uuid4()}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_thread_unauthorized(self, client, test_thread):
        """Test getting thread without authentication."""
        response = client.get(f"/threads/{test_thread.id}")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_thread_wrong_user(self, authenticated_client, test_user2, test_thread2):
        """Test getting thread owned by different user."""
        # Create a new authenticated client for test_user2
        from thread_service.auth import create_access_token

        token = create_access_token(data={"sub": str(test_user2.id), "email": test_user2.email})
        headers = {"Authorization": f"Bearer {token}"}
        response = authenticated_client.get(f"/threads/{test_thread2.id}", headers=headers)
        assert response.status_code == 200

        # But test_user should not be able to access it
        response = authenticated_client.get(f"/threads/{test_thread2.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_thread_metadata(self, authenticated_client, test_user, test_thread):
        """Test updating thread metadata."""
        updates = {"new_key": "new_value", "existing_key": "updated_value"}
        response = authenticated_client.patch(
            f"/threads/{test_thread.id}",
            json={"metadata": updates},
        )
        assert response.status_code == 200
        data = response.json()
        assert "new_key" in data["metadata"]
        assert data["metadata"]["new_key"] == "new_value"

    def test_update_thread_metadata_wrong_user(self, authenticated_client, test_user2, test_thread2):
        """Test updating thread metadata for wrong user."""
        response = authenticated_client.patch(
            f"/threads/{test_thread2.id}",
            json={"metadata": {"key": "value"}},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_append_message_minimal(self, authenticated_client, test_user, test_thread):
        """Test appending message with minimal fields."""
        response = authenticated_client.post(
            f"/threads/{test_thread.id}/messages",
            json={"content": "New message"},
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["content"] == "New message"
        assert data["kind"] == "text"
        assert data["thread_id"] == str(test_thread.id)

    def test_append_message_with_attachments(self, authenticated_client, test_user, test_thread):
        """Test appending message with attachments."""
        response = authenticated_client.post(
            f"/threads/{test_thread.id}/messages",
            json={
                "content": "Message with attachments",
                "attachments": [
                    {"uri": "s3://bucket/file1.txt", "kind": "file"},
                    {"uri": "s3://bucket/image.jpg", "kind": "image", "content_type": "image/jpeg"},
                ],
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert len(data["attachments"]) == 2
        assert data["attachments"][0]["uri"] == "s3://bucket/file1.txt"
        assert data["attachments"][1]["uri"] == "s3://bucket/image.jpg"

    def test_append_message_thread_not_found(self, authenticated_client, test_user):
        """Test appending message to non-existent thread."""
        response = authenticated_client.post(
            f"/threads/{uuid4()}/messages",
            json={"content": "Message"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_append_message_unauthorized(self, client, test_thread):
        """Test appending message without authentication."""
        response = client.post(
            f"/threads/{test_thread.id}/messages",
            json={"content": "Message"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""

    def test_signup_success(self, client, test_session):
        """Test successful user signup."""
        response = client.post(
            "/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "name": "New User",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["name"] == "New User"
        assert data["user"]["email_verified"] is False

    def test_signup_duplicate_email(self, client, test_user):
        """Test signup with duplicate email."""
        response = client.post(
            "/auth/signup",
            json={
                "email": test_user.email,
                "password": "password123",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in response.json()["detail"].lower()

    def test_login_success(self, client, test_user):
        """Test successful login."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == test_user.email

    def test_login_invalid_email(self, client):
        """Test login with invalid email."""
        response = client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_invalid_password(self, client, test_user):
        """Test login with invalid password."""
        response = client.post(
            "/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_profile(self, authenticated_client, test_user):
        """Test getting current user profile."""
        response = authenticated_client.get("/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email

    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without authentication."""
        response = client.get("/auth/me")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_current_user_profile(self, authenticated_client, test_user):
        """Test updating current user profile."""
        response = authenticated_client.put(
            "/auth/me",
            json={"name": "Updated Name", "avatar_url": "https://example.com/avatar.jpg"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["avatar_url"] == "https://example.com/avatar.jpg"

    @pytest.mark.asyncio
    async def test_verify_email_valid_token(self, client, test_user, test_session):
        """Test email verification with valid token."""
        from thread_service.auth import generate_email_verification_token, get_token_expiry
        from thread_service.repositories import create_email_verification_token

        token = generate_email_verification_token()
        expires_at = get_token_expiry(hours=24)
        await create_email_verification_token(
            test_session,
            user_id=test_user.id,
            token=token,
            expires_at=expires_at,
        )
        await test_session.commit()

        response = client.post("/auth/verify-email", json={"token": token})
        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()

    def test_verify_email_invalid_token(self, client):
        """Test email verification with invalid token."""
        response = client.post("/auth/verify-email", json={"token": "invalid_token"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_resend_verification(self, authenticated_client, test_user):
        """Test resending verification email."""
        # Ensure user is not verified
        test_user.email_verified = False
        response = authenticated_client.post("/auth/resend-verification")
        assert response.status_code == 200
        assert "sent" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_resend_verification_already_verified(self, authenticated_client, test_user, test_session):
        """Test resending verification when already verified."""
        test_user.email_verified = True
        await test_session.commit()
        response = authenticated_client.post("/auth/resend-verification")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_forgot_password(self, client, test_user):
        """Test forgot password request."""
        response = client.post("/auth/forgot-password", json={"email": test_user.email})
        assert response.status_code == 200
        # Should always return success to prevent email enumeration
        assert "sent" in response.json()["message"].lower() or "exists" in response.json()["message"].lower()

    def test_forgot_password_nonexistent_email(self, client):
        """Test forgot password with non-existent email."""
        response = client.post("/auth/forgot-password", json={"email": "nonexistent@example.com"})
        assert response.status_code == 200
        # Should still return success

    @pytest.mark.asyncio
    async def test_reset_password_valid_token(self, client, test_user, test_session):
        """Test password reset with valid token."""
        from thread_service.auth import generate_password_reset_token, get_token_expiry
        from thread_service.repositories import create_password_reset_token

        token = generate_password_reset_token()
        expires_at = get_token_expiry(hours=1)
        await create_password_reset_token(
            test_session,
            user_id=test_user.id,
            token=token,
            expires_at=expires_at,
        )
        await test_session.commit()

        response = client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": "newpassword123"},
        )
        assert response.status_code == 200
        assert "reset" in response.json()["message"].lower()

    def test_reset_password_invalid_token(self, client):
        """Test password reset with invalid token."""
        response = client.post(
            "/auth/reset-password",
            json={"token": "invalid_token", "new_password": "newpassword123"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_oauth_redirect_google(self, client):
        """Test OAuth redirect for Google."""
        response = client.get("/auth/oauth/google")
        # May return 501 if not configured, or 200 with auth_url
        assert response.status_code in [200, 501]

    def test_oauth_redirect_github(self, client):
        """Test OAuth redirect for GitHub."""
        response = client.get("/auth/oauth/github")
        # May return 501 if not configured, or 200 with auth_url
        assert response.status_code in [200, 501]

    def test_oauth_redirect_unsupported(self, client):
        """Test OAuth redirect for unsupported provider."""
        response = client.get("/auth/oauth/unsupported")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
