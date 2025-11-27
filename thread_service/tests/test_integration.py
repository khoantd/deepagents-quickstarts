"""Integration tests for end-to-end scenarios."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import status

from thread_service.auth import create_access_token, hash_password, verify_password
from thread_service.models import ThreadStatus
from thread_service.repositories import (
    append_message,
    create_thread,
    create_user,
    get_thread,
    get_user_by_email,
    list_threads,
    update_thread_metadata,
    verify_user_email,
)
from thread_service.schemas import MessageCreate, ThreadCreate


class TestUserSignupFlow:
    """Test complete user signup and email verification flow."""

    @pytest.mark.asyncio
    async def test_complete_signup_flow(self, client, test_session):
        """Test complete signup flow from registration to email verification."""
        # Step 1: Signup
        signup_response = client.post(
            "/auth/signup",
            json={
                "email": "newuser@example.com",
                "password": "password123",
                "name": "New User",
            },
        )
        assert signup_response.status_code == status.HTTP_201_CREATED
        signup_data = signup_response.json()
        assert "access_token" in signup_data
        user_id = signup_data["user"]["id"]

        # Step 2: Verify user is not verified
        user = await get_user_by_email(test_session, "newuser@example.com")
        assert user is not None
        assert user.email_verified is False

        # Step 3: Get verification token (simulated - in real flow, sent via email)
        from thread_service.auth import generate_email_verification_token, get_token_expiry
        from thread_service.repositories import create_email_verification_token, verify_email_token

        token = generate_email_verification_token()
        expires_at = get_token_expiry(hours=24)
        await create_email_verification_token(
            test_session,
            user_id=user.id,
            token=token,
            expires_at=expires_at,
        )
        await test_session.commit()

        # Step 4: Verify email
        verification_token = await verify_email_token(test_session, token)
        assert verification_token is not None

        verify_response = client.post("/auth/verify-email", json={"token": token})
        assert verify_response.status_code == 200

        # Step 5: Verify user is now verified
        await test_session.refresh(user)
        assert user.email_verified is True


class TestPasswordResetFlow:
    """Test complete password reset flow."""

    @pytest.mark.asyncio
    async def test_complete_password_reset_flow(self, client, test_user, test_session):
        """Test complete password reset flow."""
        original_password_hash = test_user.password_hash

        # Step 1: Request password reset
        reset_response = client.post("/auth/forgot-password", json={"email": test_user.email})
        assert reset_response.status_code == 200

        # Step 2: Get reset token (simulated - in real flow, sent via email)
        from thread_service.auth import generate_password_reset_token, get_token_expiry
        from thread_service.repositories import (
            create_password_reset_token,
            delete_password_reset_token,
            update_user_password,
            verify_password_reset_token,
        )

        token = generate_password_reset_token()
        expires_at = get_token_expiry(hours=1)
        await create_password_reset_token(
            test_session,
            user_id=test_user.id,
            token=token,
            expires_at=expires_at,
        )
        await test_session.commit()

        # Step 3: Verify token is valid
        reset_token = await verify_password_reset_token(test_session, token)
        assert reset_token is not None

        # Step 4: Reset password
        new_password = "newpassword123"
        reset_response = client.post(
            "/auth/reset-password",
            json={"token": token, "new_password": new_password},
        )
        assert reset_response.status_code == 200

        # Step 5: Verify password was changed
        await test_session.refresh(test_user)
        assert test_user.password_hash != original_password_hash
        assert verify_password(new_password, test_user.password_hash)

        # Step 6: Verify token was deleted
        deleted_token = await verify_password_reset_token(test_session, token)
        assert deleted_token is None

        # Step 7: Verify login with new password
        login_response = client.post(
            "/auth/login",
            json={"email": test_user.email, "password": new_password},
        )
        assert login_response.status_code == 200


class TestThreadOperationsFlow:
    """Test complete thread operations flow."""

    @pytest.mark.asyncio
    async def test_complete_thread_operations(self, authenticated_client, test_user, test_session):
        """Test complete thread operations from creation to message appending."""
        # Step 1: Create thread
        create_response = authenticated_client.post(
            "/threads",
            json={
                "title": "Integration Test Thread",
                "summary": "Test summary",
                "participants": [
                    {"role": "user", "display_name": "User 1"},
                    {"role": "agent", "display_name": "Agent 1"},
                ],
                "metadata": {"test": "value"},
            },
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        thread_data = create_response.json()
        thread_id = thread_data["id"]
        assert thread_data["title"] == "Integration Test Thread"
        assert len(thread_data["participants"]) == 2

        # Step 2: Get thread
        get_response = authenticated_client.get(f"/threads/{thread_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == thread_id

        # Step 3: Update thread metadata
        update_response = authenticated_client.patch(
            f"/threads/{thread_id}",
            json={"metadata": {"test": "updated", "new_key": "new_value"}},
        )
        assert update_response.status_code == 200
        updated_data = update_response.json()
        assert updated_data["metadata"]["test"] == "updated"
        assert updated_data["metadata"]["new_key"] == "new_value"

        # Step 4: Append messages
        message1_response = authenticated_client.post(
            f"/threads/{thread_id}/messages",
            json={"content": "First message"},
        )
        assert message1_response.status_code == status.HTTP_201_CREATED

        message2_response = authenticated_client.post(
            f"/threads/{thread_id}/messages",
            json={
                "content": "Second message with attachment",
                "attachments": [
                    {"uri": "s3://bucket/file.txt", "kind": "file", "content_type": "text/plain"},
                ],
            },
        )
        assert message2_response.status_code == status.HTTP_201_CREATED

        # Step 5: Verify thread has messages
        get_response = authenticated_client.get(f"/threads/{thread_id}")
        assert get_response.status_code == 200
        thread_data = get_response.json()
        assert len(thread_data["messages"]) == 2
        assert thread_data["messages"][0]["content"] == "First message"
        assert len(thread_data["messages"][1]["attachments"]) == 1


class TestUserIsolation:
    """Test user isolation and data access control."""

    @pytest.mark.asyncio
    async def test_user_cannot_access_other_users_threads(
        self,
        authenticated_client,
        test_user,
        test_user2,
        test_thread2,
        test_session,
    ):
        """Test that users cannot access threads belonging to other users."""
        # User 1 tries to access User 2's thread
        response = authenticated_client.get(f"/threads/{test_thread2.id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # User 1 tries to update User 2's thread
        response = authenticated_client.patch(
            f"/threads/{test_thread2.id}",
            json={"metadata": {"hacked": "value"}},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

        # User 1 tries to append message to User 2's thread
        response = authenticated_client.post(
            f"/threads/{test_thread2.id}/messages",
            json={"content": "Hacked message"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_user_only_sees_own_threads(
        self,
        authenticated_client,
        test_user,
        test_user2,
        test_thread2,
        test_session,
    ):
        """Test that users only see their own threads in list."""
        # Create thread for user 1
        create_response = authenticated_client.post(
            "/threads",
            json={"title": "User 1 Thread"},
        )
        assert create_response.status_code == status.HTTP_201_CREATED

        # List threads for user 1
        list_response = authenticated_client.get("/threads")
        assert list_response.status_code == 200
        thread_ids = [t["id"] for t in list_response.json()["threads"]]

        # User 1 should not see User 2's thread
        assert str(test_thread2.id) not in thread_ids


class TestOAuthFlow:
    """Test OAuth signup and login flow."""

    @pytest.mark.asyncio
    async def test_oauth_sync_new_user(self, client, test_session):
        """Test OAuth sync for new user."""
        oauth_response = client.post(
            "/auth/oauth/sync",
            json={
                "provider": "google",
                "provider_user_id": "google123",
                "email": "oauth@example.com",
                "name": "OAuth User",
                "avatar_url": "https://example.com/avatar.jpg",
            },
        )
        assert oauth_response.status_code == 200
        data = oauth_response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "oauth@example.com"
        assert data["user"]["email_verified"] is True

        # Verify user was created
        user = await get_user_by_email(test_session, "oauth@example.com")
        assert user is not None
        assert user.password_hash is None  # OAuth users don't have passwords
        assert user.email_verified is True

    @pytest.mark.asyncio
    async def test_oauth_sync_existing_user(self, client, test_user, test_session):
        """Test OAuth sync for existing user (account linking)."""
        oauth_response = client.post(
            "/auth/oauth/sync",
            json={
                "provider": "google",
                "provider_user_id": "google123",
                "email": test_user.email,
                "name": test_user.name,
            },
        )
        assert oauth_response.status_code == 200
        data = oauth_response.json()
        assert data["user"]["id"] == str(test_user.id)

        # Verify OAuth account was linked
        from thread_service.repositories import get_oauth_account

        oauth_account = await get_oauth_account(
            test_session,
            provider="google",
            provider_user_id="google123",
        )
        assert oauth_account is not None
        assert oauth_account.user_id == test_user.id


class TestConcurrentOperations:
    """Test concurrent operations and race conditions."""

    def test_concurrent_message_appends(self, authenticated_client, test_thread, test_session):
        """Test appending multiple messages sequentially (simulating concurrent)."""
        # Append multiple messages
        for i in range(5):
            response = authenticated_client.post(
                f"/threads/{test_thread.id}/messages",
                json={"content": f"Message {i}"},
            )
            assert response.status_code == status.HTTP_201_CREATED

        # Verify all messages are present
        get_response = authenticated_client.get(f"/threads/{test_thread.id}")
        assert get_response.status_code == 200
        messages = get_response.json()["messages"]
        assert len(messages) >= 5  # At least 5 new messages (may have existing ones)

