"""Tests for Pydantic schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import MetaData as SQLAMetaData

from thread_service.models import (
    AttachmentKind,
    MessageKind,
    ParticipantRole,
    ThreadStatus,
)
from thread_service.schemas import (
    AttachmentCreate,
    AttachmentRead,
    MessageCreate,
    MessageRead,
    ParticipantCreate,
    ParticipantRead,
    ThreadCreate,
    ThreadRead,
    ThreadUpdate,
)


class TestMetadataNormalization:
    """Test metadata normalization in schemas."""

    def test_metadata_normalize_none(self):
        """Test that None metadata is normalized to empty dict."""
        participant = ParticipantCreate(role=ParticipantRole.USER, metadata=None)
        assert participant.metadata == {}

    def test_metadata_normalize_dict(self):
        """Test that dict metadata is preserved."""
        metadata = {"key": "value", "number": 123}
        participant = ParticipantCreate(role=ParticipantRole.USER, metadata=metadata)
        assert participant.metadata == metadata

    def test_metadata_normalize_sqlalchemy_metadata(self):
        """Test that SQLAlchemy MetaData objects are normalized to empty dict."""
        sqlalchemy_metadata = SQLAMetaData()
        # This should not raise and should normalize to {}
        participant = ParticipantCreate(role=ParticipantRole.USER, metadata=sqlalchemy_metadata)
        assert participant.metadata == {}

    def test_metadata_alias_custom_metadata(self):
        """Test that custom_metadata alias works."""
        participant = ParticipantCreate(role=ParticipantRole.USER, custom_metadata={"key": "value"})
        assert participant.metadata == {"key": "value"}


class TestParticipantSchemas:
    """Test participant schemas."""

    def test_participant_create_minimal(self):
        """Test creating participant with minimal fields."""
        participant = ParticipantCreate(role=ParticipantRole.USER)
        assert participant.role == ParticipantRole.USER
        assert participant.display_name is None
        assert participant.metadata == {}

    def test_participant_create_full(self):
        """Test creating participant with all fields."""
        metadata = {"key": "value"}
        participant = ParticipantCreate(
            role=ParticipantRole.AGENT,
            display_name="Test Agent",
            metadata=metadata,
        )
        assert participant.role == ParticipantRole.AGENT
        assert participant.display_name == "Test Agent"
        assert participant.metadata == metadata

    def test_participant_read(self):
        """Test participant read schema."""
        participant_id = uuid4()
        thread_id = uuid4()
        created_at = datetime.now(timezone.utc)

        participant = ParticipantRead(
            id=participant_id,
            thread_id=thread_id,
            role=ParticipantRole.USER,
            display_name="Test",
            created_at=created_at,
            metadata={"key": "value"},
        )
        assert participant.id == participant_id
        assert participant.thread_id == thread_id
        assert participant.role == ParticipantRole.USER
        assert participant.display_name == "Test"
        assert participant.created_at == created_at
        assert participant.metadata == {"key": "value"}


class TestAttachmentSchemas:
    """Test attachment schemas."""

    def test_attachment_create_minimal(self):
        """Test creating attachment with minimal fields."""
        attachment = AttachmentCreate(uri="s3://bucket/file.txt")
        assert attachment.uri == "s3://bucket/file.txt"
        assert attachment.kind == AttachmentKind.FILE
        assert attachment.content_type is None
        assert attachment.metadata == {}

    def test_attachment_create_full(self):
        """Test creating attachment with all fields."""
        attachment = AttachmentCreate(
            kind=AttachmentKind.IMAGE,
            uri="s3://bucket/image.jpg",
            content_type="image/jpeg",
            metadata={"size": 1024},
        )
        assert attachment.kind == AttachmentKind.IMAGE
        assert attachment.uri == "s3://bucket/image.jpg"
        assert attachment.content_type == "image/jpeg"
        assert attachment.metadata == {"size": 1024}

    def test_attachment_create_missing_uri(self):
        """Test that uri is required."""
        with pytest.raises(ValidationError):
            AttachmentCreate(kind=AttachmentKind.FILE)


class TestMessageSchemas:
    """Test message schemas."""

    def test_message_create_minimal(self):
        """Test creating message with minimal fields."""
        message = MessageCreate(content="Hello")
        assert message.content == "Hello"
        assert message.kind == MessageKind.TEXT
        assert message.participant_id is None
        assert message.attachments == []
        assert message.metadata == {}

    def test_message_create_full(self):
        """Test creating message with all fields."""
        participant_id = uuid4()
        attachment = AttachmentCreate(uri="s3://bucket/file.txt")
        message = MessageCreate(
            participant_id=participant_id,
            kind=MessageKind.RICH,
            content="Hello",
            attachments=[attachment],
            metadata={"key": "value"},
        )
        assert message.participant_id == participant_id
        assert message.kind == MessageKind.RICH
        assert message.content == "Hello"
        assert len(message.attachments) == 1
        assert message.attachments[0].uri == "s3://bucket/file.txt"
        assert message.metadata == {"key": "value"}

    def test_message_create_missing_content(self):
        """Test that content is required."""
        with pytest.raises(ValidationError):
            MessageCreate(kind=MessageKind.TEXT)


class TestThreadSchemas:
    """Test thread schemas."""

    def test_thread_create_minimal(self):
        """Test creating thread with minimal fields."""
        thread = ThreadCreate()
        assert thread.title is None
        assert thread.summary is None
        assert thread.status == ThreadStatus.OPEN
        assert thread.participants == []
        assert thread.metadata == {}

    def test_thread_create_full(self):
        """Test creating thread with all fields."""
        participant = ParticipantCreate(role=ParticipantRole.USER)
        thread = ThreadCreate(
            title="Test Thread",
            summary="Test Summary",
            status=ThreadStatus.PAUSED,
            participants=[participant],
            metadata={"key": "value"},
        )
        assert thread.title == "Test Thread"
        assert thread.summary == "Test Summary"
        assert thread.status == ThreadStatus.PAUSED
        assert len(thread.participants) == 1
        assert thread.participants[0].role == ParticipantRole.USER
        assert thread.metadata == {"key": "value"}

    def test_thread_update(self):
        """Test thread update schema."""
        update = ThreadUpdate(
            title="Updated Title",
            summary="Updated Summary",
            status=ThreadStatus.CLOSED,
            metadata={"new_key": "new_value"},
        )
        assert update.title == "Updated Title"
        assert update.summary == "Updated Summary"
        assert update.status == ThreadStatus.CLOSED
        assert update.metadata == {"new_key": "new_value"}

    def test_thread_update_partial(self):
        """Test thread update with partial fields."""
        update = ThreadUpdate(title="Updated Title")
        assert update.title == "Updated Title"
        assert update.summary is None
        assert update.status is None
        assert update.metadata == {}


class TestEnumValidation:
    """Test enum validation in schemas."""

    def test_thread_status_enum(self):
        """Test ThreadStatus enum validation."""
        thread = ThreadCreate(status=ThreadStatus.OPEN)
        assert thread.status == ThreadStatus.OPEN

        thread = ThreadCreate(status="open")
        assert thread.status == ThreadStatus.OPEN

        with pytest.raises(ValidationError):
            ThreadCreate(status="invalid_status")

    def test_participant_role_enum(self):
        """Test ParticipantRole enum validation."""
        participant = ParticipantCreate(role=ParticipantRole.USER)
        assert participant.role == ParticipantRole.USER

        participant = ParticipantCreate(role="user")
        assert participant.role == ParticipantRole.USER

        with pytest.raises(ValidationError):
            ParticipantCreate(role="invalid_role")

    def test_message_kind_enum(self):
        """Test MessageKind enum validation."""
        message = MessageCreate(content="test", kind=MessageKind.TEXT)
        assert message.kind == MessageKind.TEXT

        message = MessageCreate(content="test", kind="text")
        assert message.kind == MessageKind.TEXT

        with pytest.raises(ValidationError):
            MessageCreate(content="test", kind="invalid_kind")

    def test_attachment_kind_enum(self):
        """Test AttachmentKind enum validation."""
        attachment = AttachmentCreate(uri="test", kind=AttachmentKind.FILE)
        assert attachment.kind == AttachmentKind.FILE

        attachment = AttachmentCreate(uri="test", kind="file")
        assert attachment.kind == AttachmentKind.FILE

        with pytest.raises(ValidationError):
            AttachmentCreate(uri="test", kind="invalid_kind")


class TestUUIDValidation:
    """Test UUID validation in schemas."""

    def test_participant_id_uuid(self):
        """Test participant_id UUID validation."""
        participant_id = uuid4()
        message = MessageCreate(content="test", participant_id=participant_id)
        assert message.participant_id == participant_id

        with pytest.raises(ValidationError):
            MessageCreate(content="test", participant_id="not-a-uuid")

    def test_read_schema_uuids(self):
        """Test UUID fields in read schemas."""
        thread_id = uuid4()
        participant_id = uuid4()
        message_id = uuid4()
        created_at = datetime.now(timezone.utc)

        message = MessageRead(
            id=message_id,
            thread_id=thread_id,
            participant_id=participant_id,
            kind=MessageKind.TEXT,
            content="test",
            created_at=created_at,
        )
        assert message.id == message_id
        assert message.thread_id == thread_id
        assert message.participant_id == participant_id

