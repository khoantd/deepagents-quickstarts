"""Tests for gRPC service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import grpc
import pytest
from google.protobuf import struct_pb2, timestamp_pb2

from thread_service.api.grpc import ThreadService
from thread_service.models import ThreadStatus
from thread_service.proto import thread_service_pb2 as pb2


class MockContext:
    """Mock gRPC context for testing."""

    def __init__(self):
        self.code = None
        self.details = None

    async def abort(self, code, details):
        """Mock abort method."""
        self.code = code
        self.details = details
        raise grpc.RpcError()


@pytest.fixture
def grpc_service(test_session):
    """Create a gRPC service instance with test session."""
    def session_factory():
        return test_session

    return ThreadService(session_factory=session_factory)


@pytest.fixture
def mock_context():
    """Create a mock gRPC context."""
    return MockContext()


class TestCreateThread:
    """Test CreateThread gRPC method."""

    @pytest.mark.asyncio
    async def test_create_thread_minimal(self, grpc_service, test_user, test_session):
        """Test creating thread with minimal fields."""
        request = pb2.CreateThreadRequest(title="Test Thread")
        response = await grpc_service.CreateThread(request, None)
        assert response.thread.title == "Test Thread"
        assert response.thread.status == pb2.THREAD_STATUS_OPEN
        assert response.thread.id

    @pytest.mark.asyncio
    async def test_create_thread_with_participants(self, grpc_service, test_user, test_session):
        """Test creating thread with participants."""
        request = pb2.CreateThreadRequest(
            title="Test Thread",
            participants=[
                pb2.ParticipantCreate(role=pb2.PARTICIPANT_ROLE_USER, display_name="User 1"),
                pb2.ParticipantCreate(role=pb2.PARTICIPANT_ROLE_AGENT, display_name="Agent 1"),
            ],
        )
        response = await grpc_service.CreateThread(request, None)
        assert len(response.thread.participants) == 2
        assert response.thread.participants[0].role == pb2.PARTICIPANT_ROLE_USER
        assert response.thread.participants[1].role == pb2.PARTICIPANT_ROLE_AGENT

    @pytest.mark.asyncio
    async def test_create_thread_with_metadata(self, grpc_service, test_user, test_session):
        """Test creating thread with metadata."""
        metadata = struct_pb2.Struct()
        metadata.update({"key": "value", "number": 123})
        request = pb2.CreateThreadRequest(title="Test Thread", metadata=metadata)
        response = await grpc_service.CreateThread(request, None)
        # Verify metadata is preserved
        assert response.thread.metadata["key"] == "value"
        assert response.thread.metadata["number"] == 123


class TestAppendMessage:
    """Test AppendMessage gRPC method."""

    @pytest.mark.asyncio
    async def test_append_message_minimal(self, grpc_service, test_thread, test_session):
        """Test appending message with minimal fields."""
        request = pb2.AppendMessageRequest(
            thread_id=str(test_thread.id),
            content="Test message",
        )
        response = await grpc_service.AppendMessage(request, None)
        assert response.message.content == "Test message"
        assert response.message.thread_id == str(test_thread.id)
        assert response.message.kind == pb2.MESSAGE_KIND_TEXT

    @pytest.mark.asyncio
    async def test_append_message_with_attachments(self, grpc_service, test_thread, test_session):
        """Test appending message with attachments."""
        request = pb2.AppendMessageRequest(
            thread_id=str(test_thread.id),
            content="Message with attachments",
            attachments=[
                pb2.AttachmentCreate(uri="s3://bucket/file1.txt", kind=pb2.ATTACHMENT_KIND_FILE),
                pb2.AttachmentCreate(uri="s3://bucket/image.jpg", kind=pb2.ATTACHMENT_KIND_IMAGE),
            ],
        )
        response = await grpc_service.AppendMessage(request, None)
        assert len(response.message.attachments) == 2
        assert response.message.attachments[0].uri == "s3://bucket/file1.txt"
        assert response.message.attachments[1].uri == "s3://bucket/image.jpg"

    @pytest.mark.asyncio
    async def test_append_message_thread_not_found(self, grpc_service, mock_context, test_session):
        """Test appending message to non-existent thread."""
        request = pb2.AppendMessageRequest(
            thread_id=str(uuid4()),
            content="Test message",
        )
        with pytest.raises(grpc.RpcError):
            await grpc_service.AppendMessage(request, mock_context)
        assert mock_context.code == grpc.StatusCode.NOT_FOUND


class TestGetThread:
    """Test GetThread gRPC method."""

    @pytest.mark.asyncio
    async def test_get_thread_success(self, grpc_service, test_thread, test_session):
        """Test getting thread successfully."""
        request = pb2.GetThreadRequest(thread_id=str(test_thread.id))
        response = await grpc_service.GetThread(request, None)
        assert response.thread.id == str(test_thread.id)
        assert response.thread.title == test_thread.title
        assert len(response.thread.participants) > 0
        assert len(response.thread.messages) > 0

    @pytest.mark.asyncio
    async def test_get_thread_not_found(self, grpc_service, mock_context, test_session):
        """Test getting non-existent thread."""
        request = pb2.GetThreadRequest(thread_id=str(uuid4()))
        with pytest.raises(grpc.RpcError):
            await grpc_service.GetThread(request, mock_context)
        assert mock_context.code == grpc.StatusCode.NOT_FOUND


class TestListThreads:
    """Test ListThreads gRPC method."""

    @pytest.mark.asyncio
    async def test_list_threads_default(self, grpc_service, test_thread, test_session):
        """Test listing threads with default parameters."""
        request = pb2.ListThreadsRequest()
        response = await grpc_service.ListThreads(request, None)
        assert response.total >= 1
        assert len(response.threads) > 0

    @pytest.mark.asyncio
    async def test_list_threads_pagination(self, grpc_service, multiple_threads, test_session):
        """Test listing threads with pagination."""
        request = pb2.ListThreadsRequest(limit=2, offset=0)
        response = await grpc_service.ListThreads(request, None)
        assert len(response.threads) == 2
        assert response.total == 5

    @pytest.mark.asyncio
    async def test_list_threads_status_filter(self, grpc_service, multiple_threads, test_session):
        """Test listing threads with status filter."""
        request = pb2.ListThreadsRequest(status=pb2.THREAD_STATUS_OPEN)
        response = await grpc_service.ListThreads(request, None)
        assert all(thread.status == pb2.THREAD_STATUS_OPEN for thread in response.threads)

    @pytest.mark.asyncio
    async def test_list_threads_date_filters(self, grpc_service, test_thread, test_session):
        """Test listing threads with date filters."""
        created_after = timestamp_pb2.Timestamp()
        created_after.FromDatetime(datetime.now(timezone.utc) - timedelta(days=1))
        created_before = timestamp_pb2.Timestamp()
        created_before.FromDatetime(datetime.now(timezone.utc) + timedelta(days=1))

        request = pb2.ListThreadsRequest(
            created_after=created_after,
            created_before=created_before,
        )
        response = await grpc_service.ListThreads(request, None)
        assert response.total >= 0


class TestStreamThreadMessages:
    """Test StreamThreadMessages gRPC method."""

    @pytest.mark.asyncio
    async def test_stream_thread_messages_success(self, grpc_service, test_thread, test_session):
        """Test streaming thread messages successfully."""
        request = pb2.StreamThreadMessagesRequest(thread_id=str(test_thread.id))
        messages = []
        async for message in grpc_service.StreamThreadMessages(request, None):
            messages.append(message)
        assert len(messages) > 0
        assert all(msg.thread_id == str(test_thread.id) for msg in messages)

    @pytest.mark.asyncio
    async def test_stream_thread_messages_not_found(self, grpc_service, mock_context, test_session):
        """Test streaming messages for non-existent thread."""
        request = pb2.StreamThreadMessagesRequest(thread_id=str(uuid4()))
        with pytest.raises(grpc.RpcError):
            async for _ in grpc_service.StreamThreadMessages(request, mock_context):
                pass
        assert mock_context.code == grpc.StatusCode.NOT_FOUND


class TestProtocolBufferConversions:
    """Test protocol buffer conversion utilities."""

    @pytest.mark.asyncio
    async def test_thread_status_conversion(self, grpc_service, test_user, test_session):
        """Test ThreadStatus enum conversion."""
        # Test OPEN
        request = pb2.CreateThreadRequest(title="Test", status=pb2.THREAD_STATUS_OPEN)
        response = await grpc_service.CreateThread(request, None)
        assert response.thread.status == pb2.THREAD_STATUS_OPEN

        # Test PAUSED
        request = pb2.CreateThreadRequest(title="Test", status=pb2.THREAD_STATUS_PAUSED)
        response = await grpc_service.CreateThread(request, None)
        assert response.thread.status == pb2.THREAD_STATUS_PAUSED

    @pytest.mark.asyncio
    async def test_participant_role_conversion(self, grpc_service, test_user, test_session):
        """Test ParticipantRole enum conversion."""
        request = pb2.CreateThreadRequest(
            title="Test",
            participants=[
                pb2.ParticipantCreate(role=pb2.PARTICIPANT_ROLE_USER),
                pb2.ParticipantCreate(role=pb2.PARTICIPANT_ROLE_AGENT),
                pb2.ParticipantCreate(role=pb2.PARTICIPANT_ROLE_TOOL),
            ],
        )
        response = await grpc_service.CreateThread(request, None)
        assert response.thread.participants[0].role == pb2.PARTICIPANT_ROLE_USER
        assert response.thread.participants[1].role == pb2.PARTICIPANT_ROLE_AGENT
        assert response.thread.participants[2].role == pb2.PARTICIPANT_ROLE_TOOL

    @pytest.mark.asyncio
    async def test_message_kind_conversion(self, grpc_service, test_thread, test_session):
        """Test MessageKind enum conversion."""
        request = pb2.AppendMessageRequest(
            thread_id=str(test_thread.id),
            content="Test",
            kind=pb2.MESSAGE_KIND_RICH,
        )
        response = await grpc_service.AppendMessage(request, None)
        assert response.message.kind == pb2.MESSAGE_KIND_RICH

    @pytest.mark.asyncio
    async def test_timestamp_conversion(self, grpc_service, test_thread, test_session):
        """Test timestamp conversion in thread response."""
        request = pb2.GetThreadRequest(thread_id=str(test_thread.id))
        response = await grpc_service.GetThread(request, None)
        # Verify timestamps are present and valid
        assert response.thread.created_at.seconds > 0
        assert response.thread.updated_at.seconds > 0

    @pytest.mark.asyncio
    async def test_metadata_serialization(self, grpc_service, test_user, test_session):
        """Test metadata serialization in protocol buffers."""
        metadata = struct_pb2.Struct()
        metadata.update({
            "string": "value",
            "number": 123,
            "boolean": True,
            "nested": {"inner": "value"},
        })
        request = pb2.CreateThreadRequest(title="Test", metadata=metadata)
        response = await grpc_service.CreateThread(request, None)
        assert response.thread.metadata["string"] == "value"
        assert response.thread.metadata["number"] == 123
        assert response.thread.metadata["boolean"] is True
        assert response.thread.metadata["nested"]["inner"] == "value"

