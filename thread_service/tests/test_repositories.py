"""Tests for repository functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import NoResultFound

from thread_service.models import (
    AttachmentKind,
    EmailVerificationToken,
    Message,
    MessageAttachment,
    MessageKind,
    OAuthAccount,
    Participant,
    ParticipantRole,
    PasswordResetToken,
    Thread,
    ThreadStatus,
    User,
)
from thread_service.repositories import (
    append_message,
    create_email_verification_token,
    create_oauth_account,
    create_password_reset_token,
    create_thread,
    create_user,
    delete_password_reset_token,
    get_oauth_account,
    get_thread,
    get_user_by_email,
    get_user_by_id,
    list_threads,
    update_thread_metadata,
    update_user_password,
    verify_email_token,
    verify_password_reset_token,
    verify_user_email,
)
from thread_service.schemas import (
    AttachmentCreate,
    MessageCreate,
    ParticipantCreate,
    ThreadCreate,
)


class TestUserRepository:
    """Test user repository functions."""

    @pytest.mark.asyncio
    async def test_create_user_with_password(self, test_session):
        """Test creating a user with password."""
        user = await create_user(
            test_session,
            email="newuser@example.com",
            password_hash="hashed_password",
            name="New User",
        )
        assert user.email == "newuser@example.com"
        assert user.password_hash == "hashed_password"
        assert user.name == "New User"
        assert user.email_verified is False
        assert user.id is not None

    @pytest.mark.asyncio
    async def test_create_user_oauth(self, test_session):
        """Test creating an OAuth user without password."""
        user = await create_user(
            test_session,
            email="oauth@example.com",
            password_hash=None,
            name="OAuth User",
        )
        assert user.email == "oauth@example.com"
        assert user.password_hash is None
        assert user.name == "OAuth User"

    @pytest.mark.asyncio
    async def test_get_user_by_email_found(self, test_user, test_session):
        """Test getting user by email when found."""
        user = await get_user_by_email(test_session, test_user.email)
        assert user is not None
        assert user.id == test_user.id
        assert user.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, test_session):
        """Test getting user by email when not found."""
        user = await get_user_by_email(test_session, "nonexistent@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_found(self, test_user, test_session):
        """Test getting user by ID when found."""
        user = await get_user_by_id(test_session, test_user.id)
        assert user is not None
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, test_session):
        """Test getting user by ID when not found."""
        user = await get_user_by_id(test_session, uuid4())
        assert user is None

    @pytest.mark.asyncio
    async def test_verify_user_email(self, test_user, test_session):
        """Test verifying user email."""
        assert test_user.email_verified is False
        updated_user = await verify_user_email(test_session, test_user.id)
        assert updated_user.email_verified is True

    @pytest.mark.asyncio
    async def test_verify_user_email_not_found(self, test_session):
        """Test verifying email for non-existent user."""
        with pytest.raises(NoResultFound):
            await verify_user_email(test_session, uuid4())

    @pytest.mark.asyncio
    async def test_update_user_password(self, test_user, test_session):
        """Test updating user password."""
        new_hash = "new_hashed_password"
        updated_user = await update_user_password(test_session, test_user.id, new_hash)
        assert updated_user.password_hash == new_hash

    @pytest.mark.asyncio
    async def test_update_user_password_not_found(self, test_session):
        """Test updating password for non-existent user."""
        with pytest.raises(NoResultFound):
            await update_user_password(test_session, uuid4(), "new_hash")


class TestOAuthRepository:
    """Test OAuth account repository functions."""

    @pytest.mark.asyncio
    async def test_create_oauth_account_new(self, test_user, test_session):
        """Test creating a new OAuth account."""
        oauth_account = await create_oauth_account(
            test_session,
            user_id=test_user.id,
            provider="google",
            provider_user_id="google123",
            access_token="token123",
        )
        assert oauth_account.user_id == test_user.id
        assert oauth_account.provider == "google"
        assert oauth_account.provider_user_id == "google123"
        assert oauth_account.access_token == "token123"

    @pytest.mark.asyncio
    async def test_create_oauth_account_update_existing(self, test_user, test_session):
        """Test updating an existing OAuth account."""
        # Create initial account
        account1 = await create_oauth_account(
            test_session,
            user_id=test_user.id,
            provider="google",
            provider_user_id="google123",
            access_token="token1",
        )
        # Update with new token
        account2 = await create_oauth_account(
            test_session,
            user_id=test_user.id,
            provider="google",
            provider_user_id="google123",
            access_token="token2",
        )
        assert account1.id == account2.id
        assert account2.access_token == "token2"

    @pytest.mark.asyncio
    async def test_get_oauth_account_found(self, test_user, test_session):
        """Test getting OAuth account when found."""
        await create_oauth_account(
            test_session,
            user_id=test_user.id,
            provider="google",
            provider_user_id="google123",
        )
        account = await get_oauth_account(
            test_session,
            provider="google",
            provider_user_id="google123",
        )
        assert account is not None
        assert account.provider == "google"
        assert account.provider_user_id == "google123"

    @pytest.mark.asyncio
    async def test_get_oauth_account_not_found(self, test_session):
        """Test getting OAuth account when not found."""
        account = await get_oauth_account(
            test_session,
            provider="google",
            provider_user_id="nonexistent",
        )
        assert account is None


class TestTokenRepository:
    """Test token repository functions."""

    @pytest.mark.asyncio
    async def test_create_email_verification_token(self, test_user, test_session):
        """Test creating email verification token."""
        token = "test_token_123"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        verification_token = await create_email_verification_token(
            test_session,
            user_id=test_user.id,
            token=token,
            expires_at=expires_at,
        )
        assert verification_token.user_id == test_user.id
        assert verification_token.token == token
        assert verification_token.expires_at == expires_at

    @pytest.mark.asyncio
    async def test_verify_email_token_valid(self, test_user, test_session):
        """Test verifying valid email token."""
        token = "valid_token"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        await create_email_verification_token(
            test_session,
            user_id=test_user.id,
            token=token,
            expires_at=expires_at,
        )
        verification_token = await verify_email_token(test_session, token)
        assert verification_token is not None
        assert verification_token.token == token

    @pytest.mark.asyncio
    async def test_verify_email_token_expired(self, test_user, test_session):
        """Test verifying expired email token."""
        token = "expired_token"
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await create_email_verification_token(
            test_session,
            user_id=test_user.id,
            token=token,
            expires_at=expires_at,
        )
        verification_token = await verify_email_token(test_session, token)
        assert verification_token is None

    @pytest.mark.asyncio
    async def test_verify_email_token_invalid(self, test_session):
        """Test verifying invalid email token."""
        verification_token = await verify_email_token(test_session, "invalid_token")
        assert verification_token is None

    @pytest.mark.asyncio
    async def test_create_password_reset_token(self, test_user, test_session):
        """Test creating password reset token."""
        token = "reset_token_123"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        reset_token = await create_password_reset_token(
            test_session,
            user_id=test_user.id,
            token=token,
            expires_at=expires_at,
        )
        assert reset_token.user_id == test_user.id
        assert reset_token.token == token
        assert reset_token.expires_at == expires_at

    @pytest.mark.asyncio
    async def test_verify_password_reset_token_valid(self, test_user, test_session):
        """Test verifying valid password reset token."""
        token = "valid_reset_token"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await create_password_reset_token(
            test_session,
            user_id=test_user.id,
            token=token,
            expires_at=expires_at,
        )
        reset_token = await verify_password_reset_token(test_session, token)
        assert reset_token is not None
        assert reset_token.token == token

    @pytest.mark.asyncio
    async def test_verify_password_reset_token_expired(self, test_user, test_session):
        """Test verifying expired password reset token."""
        token = "expired_reset_token"
        expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await create_password_reset_token(
            test_session,
            user_id=test_user.id,
            token=token,
            expires_at=expires_at,
        )
        reset_token = await verify_password_reset_token(test_session, token)
        assert reset_token is None

    @pytest.mark.asyncio
    async def test_verify_password_reset_token_invalid(self, test_session):
        """Test verifying invalid password reset token."""
        reset_token = await verify_password_reset_token(test_session, "invalid_token")
        assert reset_token is None

    @pytest.mark.asyncio
    async def test_delete_password_reset_token(self, test_user, test_session):
        """Test deleting password reset token."""
        token = "token_to_delete"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await create_password_reset_token(
            test_session,
            user_id=test_user.id,
            token=token,
            expires_at=expires_at,
        )
        # Verify it exists
        reset_token = await verify_password_reset_token(test_session, token)
        assert reset_token is not None
        # Delete it
        await delete_password_reset_token(test_session, token)
        # Verify it's gone
        reset_token = await verify_password_reset_token(test_session, token)
        assert reset_token is None


class TestThreadRepository:
    """Test thread repository functions."""

    @pytest.mark.asyncio
    async def test_create_thread_minimal(self, test_user, test_session):
        """Test creating thread with minimal fields."""
        payload = ThreadCreate(title="Test Thread")
        thread = await create_thread(test_session, payload, user_id=test_user.id)
        assert thread.title == "Test Thread"
        assert thread.user_id == test_user.id
        assert thread.status == ThreadStatus.OPEN
        assert thread.summary is None
        assert thread.custom_metadata == {}

    @pytest.mark.asyncio
    async def test_create_thread_with_participants(self, test_user, test_session):
        """Test creating thread with participants."""
        payload = ThreadCreate(
            title="Test Thread",
            participants=[
                ParticipantCreate(role=ParticipantRole.USER, display_name="User 1"),
                ParticipantCreate(role=ParticipantRole.AGENT, display_name="Agent 1"),
            ],
        )
        thread = await create_thread(test_session, payload, user_id=test_user.id)
        assert len(thread.participants) == 2
        assert thread.participants[0].role == ParticipantRole.USER
        assert thread.participants[1].role == ParticipantRole.AGENT

    @pytest.mark.asyncio
    async def test_create_thread_with_metadata(self, test_user, test_session):
        """Test creating thread with metadata."""
        metadata = {"key": "value", "number": 123}
        payload = ThreadCreate(title="Test Thread", metadata=metadata)
        thread = await create_thread(test_session, payload, user_id=test_user.id)
        assert thread.custom_metadata == metadata

    @pytest.mark.asyncio
    async def test_list_threads_pagination(self, test_user, test_session):
        """Test listing threads with pagination."""
        # Create multiple threads
        for i in range(5):
            payload = ThreadCreate(title=f"Thread {i}")
            await create_thread(test_session, payload, user_id=test_user.id)

        threads, total = await list_threads(
            test_session,
            user_id=test_user.id,
            limit=2,
            offset=0,
        )
        assert len(threads) == 2
        assert total == 5

        threads, total = await list_threads(
            test_session,
            user_id=test_user.id,
            limit=2,
            offset=2,
        )
        assert len(threads) == 2
        assert total == 5

    @pytest.mark.asyncio
    async def test_list_threads_status_filter(self, test_user, test_session):
        """Test listing threads with status filter."""
        # Create threads with different statuses
        payload1 = ThreadCreate(title="Open Thread", status=ThreadStatus.OPEN)
        await create_thread(test_session, payload1, user_id=test_user.id)
        payload2 = ThreadCreate(title="Paused Thread", status=ThreadStatus.PAUSED)
        await create_thread(test_session, payload2, user_id=test_user.id)

        threads, total = await list_threads(
            test_session,
            user_id=test_user.id,
            limit=10,
            offset=0,
            status=ThreadStatus.OPEN,
        )
        assert total == 1
        assert threads[0].status == ThreadStatus.OPEN

    @pytest.mark.asyncio
    async def test_list_threads_user_scoping(self, test_user, test_user2, test_session):
        """Test that threads are scoped to user."""
        # Create thread for user1
        payload1 = ThreadCreate(title="User1 Thread")
        await create_thread(test_session, payload1, user_id=test_user.id)
        # Create thread for user2
        payload2 = ThreadCreate(title="User2 Thread")
        await create_thread(test_session, payload2, user_id=test_user2.id)

        # List threads for user1
        threads, total = await list_threads(
            test_session,
            user_id=test_user.id,
            limit=10,
            offset=0,
        )
        assert total == 1
        assert threads[0].title == "User1 Thread"

    @pytest.mark.asyncio
    async def test_get_thread_found(self, test_thread, test_user, test_session):
        """Test getting thread when found."""
        thread = await get_thread(test_session, test_thread.id, user_id=test_user.id)
        assert thread.id == test_thread.id
        assert thread.title == test_thread.title
        assert len(thread.participants) > 0
        assert len(thread.messages) > 0

    @pytest.mark.asyncio
    async def test_get_thread_not_found(self, test_session, test_user):
        """Test getting thread when not found."""
        with pytest.raises(NoResultFound):
            await get_thread(test_session, uuid4(), user_id=test_user.id)

    @pytest.mark.asyncio
    async def test_get_thread_wrong_user(self, test_thread, test_user2, test_session):
        """Test getting thread owned by different user."""
        with pytest.raises(NoResultFound):
            await get_thread(test_session, test_thread.id, user_id=test_user2.id)

    @pytest.mark.asyncio
    async def test_update_thread_metadata(self, test_thread, test_user, test_session):
        """Test updating thread metadata."""
        updates = {"new_key": "new_value", "existing_key": "updated_value"}
        updated_thread = await update_thread_metadata(
            test_session,
            thread_id=test_thread.id,
            user_id=test_user.id,
            metadata_updates=updates,
        )
        # Should merge with existing metadata
        assert "new_key" in updated_thread.custom_metadata
        assert updated_thread.custom_metadata["new_key"] == "new_value"
        # Should update existing keys
        assert updated_thread.custom_metadata.get("existing_key") == "updated_value"

    @pytest.mark.asyncio
    async def test_update_thread_metadata_wrong_user(self, test_thread, test_user2, test_session):
        """Test updating thread metadata for wrong user."""
        with pytest.raises(NoResultFound):
            await update_thread_metadata(
                test_session,
                thread_id=test_thread.id,
                user_id=test_user2.id,
                metadata_updates={"key": "value"},
            )

    @pytest.mark.asyncio
    async def test_append_message_minimal(self, test_thread, test_session):
        """Test appending message with minimal fields."""
        payload = MessageCreate(content="Test message")
        message = await append_message(test_session, thread_id=test_thread.id, payload=payload)
        assert message.content == "Test message"
        assert message.thread_id == test_thread.id
        assert message.kind == MessageKind.TEXT
        assert message.participant_id is None
        assert len(message.attachments) == 0

    @pytest.mark.asyncio
    async def test_append_message_with_attachments(self, test_thread, test_session):
        """Test appending message with attachments."""
        payload = MessageCreate(
            content="Test message",
            attachments=[
                AttachmentCreate(uri="s3://bucket/file1.txt", kind=AttachmentKind.FILE),
                AttachmentCreate(uri="s3://bucket/image.jpg", kind=AttachmentKind.IMAGE),
            ],
        )
        message = await append_message(test_session, thread_id=test_thread.id, payload=payload)
        assert len(message.attachments) == 2
        assert message.attachments[0].uri == "s3://bucket/file1.txt"
        assert message.attachments[1].uri == "s3://bucket/image.jpg"

    @pytest.mark.asyncio
    async def test_append_message_thread_not_found(self, test_session):
        """Test appending message to non-existent thread."""
        payload = MessageCreate(content="Test message")
        with pytest.raises(NoResultFound):
            await append_message(test_session, thread_id=uuid4(), payload=payload)

