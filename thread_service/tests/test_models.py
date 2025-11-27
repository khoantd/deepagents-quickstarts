"""Tests for SQLAlchemy models."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from thread_service.models import (
    AttachmentKind,
    AttachmentKindType,
    Message,
    MessageAttachment,
    MessageKind,
    MessageKindType,
    Participant,
    ParticipantRole,
    ParticipantRoleType,
    Thread,
    ThreadStatus,
    ThreadStatusType,
    User,
)


class TestEnumTypeDecorators:
    """Test enum type decorators."""

    def test_thread_status_type_bind(self):
        """Test ThreadStatusType process_bind_param."""
        decorator = ThreadStatusType()
        assert decorator.process_bind_param(ThreadStatus.OPEN, None) == "open"
        assert decorator.process_bind_param(ThreadStatus.PAUSED, None) == "paused"
        assert decorator.process_bind_param(ThreadStatus.CLOSED, None) == "closed"
        assert decorator.process_bind_param(None, None) is None
        assert decorator.process_bind_param("open", None) == "open"

    def test_thread_status_type_result(self):
        """Test ThreadStatusType process_result_value."""
        decorator = ThreadStatusType()
        assert decorator.process_result_value("open", None) == ThreadStatus.OPEN
        assert decorator.process_result_value("paused", None) == ThreadStatus.PAUSED
        assert decorator.process_result_value("closed", None) == ThreadStatus.CLOSED
        assert decorator.process_result_value(None, None) is None

    def test_thread_status_type_case_insensitive(self):
        """Test ThreadStatusType case-insensitive matching."""
        decorator = ThreadStatusType()
        assert decorator.process_result_value("OPEN", None) == ThreadStatus.OPEN
        assert decorator.process_result_value("Open", None) == ThreadStatus.OPEN

    def test_participant_role_type(self):
        """Test ParticipantRoleType."""
        decorator = ParticipantRoleType()
        assert decorator.process_bind_param(ParticipantRole.USER, None) == "user"
        assert decorator.process_result_value("user", None) == ParticipantRole.USER
        assert decorator.process_result_value("USER", None) == ParticipantRole.USER

    def test_message_kind_type(self):
        """Test MessageKindType."""
        decorator = MessageKindType()
        assert decorator.process_bind_param(MessageKind.TEXT, None) == "text"
        assert decorator.process_result_value("text", None) == MessageKind.TEXT
        assert decorator.process_result_value("TEXT", None) == MessageKind.TEXT

    def test_attachment_kind_type(self):
        """Test AttachmentKindType."""
        decorator = AttachmentKindType()
        assert decorator.process_bind_param(AttachmentKind.FILE, None) == "file"
        assert decorator.process_result_value("file", None) == AttachmentKind.FILE
        assert decorator.process_result_value("FILE", None) == AttachmentKind.FILE


class TestUserModel:
    """Test User model."""

    @pytest.mark.asyncio
    async def test_user_creation(self, test_session):
        """Test creating a user."""
        user = User(
            email="test@example.com",
            password_hash="hashed",
            name="Test User",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed"
        assert user.name == "Test User"
        assert user.email_verified is False
        assert user.id is not None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_user_threads_relationship(self, test_user, test_thread, test_session):
        """Test user-threads relationship."""
        await test_session.refresh(test_user, attribute_names=["threads"])
        assert len(test_user.threads) > 0
        assert test_user.threads[0].id == test_thread.id


class TestThreadModel:
    """Test Thread model."""

    @pytest.mark.asyncio
    async def test_thread_creation(self, test_user, test_session):
        """Test creating a thread."""
        thread = Thread(
            user_id=test_user.id,
            title="Test Thread",
            status=ThreadStatus.OPEN,
            summary="Test summary",
            custom_metadata={"key": "value"},
        )
        test_session.add(thread)
        await test_session.commit()
        await test_session.refresh(thread)
        assert thread.title == "Test Thread"
        assert thread.status == ThreadStatus.OPEN
        assert thread.summary == "Test summary"
        assert thread.custom_metadata == {"key": "value"}
        assert thread.user_id == test_user.id
        assert isinstance(thread.created_at, datetime)
        assert isinstance(thread.updated_at, datetime)

    @pytest.mark.asyncio
    async def test_thread_participants_relationship(self, test_thread, test_session):
        """Test thread-participants relationship."""
        await test_session.refresh(test_thread, attribute_names=["participants"])
        assert len(test_thread.participants) > 0
        assert test_thread.participants[0].thread_id == test_thread.id

    @pytest.mark.asyncio
    async def test_thread_messages_relationship(self, test_thread, test_session):
        """Test thread-messages relationship."""
        await test_session.refresh(test_thread, attribute_names=["messages"])
        assert len(test_thread.messages) > 0
        assert test_thread.messages[0].thread_id == test_thread.id


class TestParticipantModel:
    """Test Participant model."""

    @pytest.mark.asyncio
    async def test_participant_creation(self, test_thread, test_session):
        """Test creating a participant."""
        participant = Participant(
            thread_id=test_thread.id,
            role=ParticipantRole.USER,
            display_name="Test Participant",
            custom_metadata={"key": "value"},
        )
        test_session.add(participant)
        await test_session.commit()
        await test_session.refresh(participant)
        assert participant.thread_id == test_thread.id
        assert participant.role == ParticipantRole.USER
        assert participant.display_name == "Test Participant"
        assert participant.custom_metadata == {"key": "value"}
        assert isinstance(participant.created_at, datetime)

    @pytest.mark.asyncio
    async def test_participant_messages_relationship(self, test_thread, test_session):
        """Test participant-messages relationship."""
        await test_session.refresh(test_thread, attribute_names=["participants", "messages"])
        participant = test_thread.participants[0]
        await test_session.refresh(participant, attribute_names=["messages"])
        assert len(participant.messages) > 0
        assert participant.messages[0].participant_id == participant.id


class TestMessageModel:
    """Test Message model."""

    @pytest.mark.asyncio
    async def test_message_creation(self, test_thread, test_session):
        """Test creating a message."""
        participant = test_thread.participants[0] if test_thread.participants else None
        message = Message(
            thread_id=test_thread.id,
            participant_id=participant.id if participant else None,
            kind=MessageKind.TEXT,
            content="Test message",
            custom_metadata={"key": "value"},
        )
        test_session.add(message)
        await test_session.commit()
        await test_session.refresh(message)
        assert message.thread_id == test_thread.id
        assert message.kind == MessageKind.TEXT
        assert message.content == "Test message"
        assert message.custom_metadata == {"key": "value"}
        assert isinstance(message.created_at, datetime)

    @pytest.mark.asyncio
    async def test_message_attachments_relationship(self, test_thread, test_session):
        """Test message-attachments relationship."""
        await test_session.refresh(test_thread, attribute_names=["messages"])
        message = test_thread.messages[0]
        await test_session.refresh(message, attribute_names=["attachments"])
        assert len(message.attachments) > 0
        assert message.attachments[0].message_id == message.id


class TestMessageAttachmentModel:
    """Test MessageAttachment model."""

    @pytest.mark.asyncio
    async def test_attachment_creation(self, test_thread, test_session):
        """Test creating a message attachment."""
        await test_session.refresh(test_thread, attribute_names=["messages"])
        message = test_thread.messages[0]
        attachment = MessageAttachment(
            message_id=message.id,
            kind=AttachmentKind.FILE,
            uri="s3://bucket/file.txt",
            content_type="text/plain",
            custom_metadata={"key": "value"},
        )
        test_session.add(attachment)
        await test_session.commit()
        await test_session.refresh(attachment)
        assert attachment.message_id == message.id
        assert attachment.kind == AttachmentKind.FILE
        assert attachment.uri == "s3://bucket/file.txt"
        assert attachment.content_type == "text/plain"
        assert attachment.custom_metadata == {"key": "value"}
        assert isinstance(attachment.created_at, datetime)


class TestJSONBMetadata:
    """Test JSONB metadata handling."""

    @pytest.mark.asyncio
    async def test_thread_metadata_dict(self, test_user, test_session):
        """Test thread metadata as dict."""
        metadata = {"key": "value", "number": 123, "nested": {"inner": "value"}}
        thread = Thread(
            user_id=test_user.id,
            title="Test",
            custom_metadata=metadata,
        )
        test_session.add(thread)
        await test_session.commit()
        await test_session.refresh(thread)
        assert thread.custom_metadata == metadata

    @pytest.mark.asyncio
    async def test_thread_metadata_empty(self, test_user, test_session):
        """Test thread metadata as empty dict."""
        thread = Thread(
            user_id=test_user.id,
            title="Test",
            custom_metadata={},
        )
        test_session.add(thread)
        await test_session.commit()
        await test_session.refresh(thread)
        assert thread.custom_metadata == {}


class TestTimestampDefaults:
    """Test timestamp defaults and updates."""

    @pytest.mark.asyncio
    async def test_user_timestamps(self, test_session):
        """Test user created_at and updated_at."""
        user = User(
            email="timestamp@example.com",
            password_hash="hash",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.created_at.tzinfo == timezone.utc
        assert user.updated_at.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_thread_updated_at_updates(self, test_user, test_session):
        """Test that thread updated_at updates on change."""
        thread = Thread(
            user_id=test_user.id,
            title="Original",
        )
        test_session.add(thread)
        await test_session.commit()
        await test_session.refresh(thread)
        original_updated = thread.updated_at

        # Update thread
        thread.title = "Updated"
        await test_session.commit()
        await test_session.refresh(thread)
        assert thread.updated_at > original_updated

