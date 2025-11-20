"""gRPC service bindings for thread persistence."""

from __future__ import annotations

from datetime import timezone
from typing import Any
from uuid import UUID

import grpc
from google.protobuf import struct_pb2, timestamp_pb2
from google.protobuf.json_format import MessageToDict, ParseDict
from sqlalchemy.exc import NoResultFound

from ..db import SessionLocal
from ..models import AttachmentKind, MessageKind, ParticipantRole, ThreadStatus
from ..repositories import append_message, create_thread, get_thread, list_threads
from ..schemas import AttachmentCreate, MessageCreate, ParticipantCreate, ThreadCreate
from ..proto import thread_service_pb2 as pb2
from ..proto import thread_service_pb2_grpc as pb2_grpc


def _struct_to_dict(struct: struct_pb2.Struct | None) -> dict[str, Any]:
    if not struct:
        return {}
    return MessageToDict(struct, preserving_proto_field_name=True)


def _dict_to_struct(data: dict[str, Any] | None) -> struct_pb2.Struct:
    struct = struct_pb2.Struct()
    ParseDict(data or {}, struct, ignore_unknown_fields=True)
    return struct


def _timestamp_from_datetime(dt):  # type: ignore[no-untyped-def]
    stamp = timestamp_pb2.Timestamp()
    if dt is None:
        return stamp
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    stamp.FromDatetime(dt.astimezone(timezone.utc))
    return stamp


_PB_TO_THREAD_STATUS = {
    pb2.THREAD_STATUS_OPEN: ThreadStatus.OPEN,
    pb2.THREAD_STATUS_PAUSED: ThreadStatus.PAUSED,
    pb2.THREAD_STATUS_CLOSED: ThreadStatus.CLOSED,
}
_THREAD_STATUS_TO_PB = {v: k for k, v in _PB_TO_THREAD_STATUS.items()}

_PB_TO_PARTICIPANT_ROLE = {
    pb2.PARTICIPANT_ROLE_USER: ParticipantRole.USER,
    pb2.PARTICIPANT_ROLE_AGENT: ParticipantRole.AGENT,
    pb2.PARTICIPANT_ROLE_TOOL: ParticipantRole.TOOL,
}
_PARTICIPANT_ROLE_TO_PB = {v: k for k, v in _PB_TO_PARTICIPANT_ROLE.items()}

_PB_TO_MESSAGE_KIND = {
    pb2.MESSAGE_KIND_TEXT: MessageKind.TEXT,
    pb2.MESSAGE_KIND_RICH: MessageKind.RICH,
    pb2.MESSAGE_KIND_TOOL_CALL: MessageKind.TOOL_CALL,
}
_MESSAGE_KIND_TO_PB = {v: k for k, v in _PB_TO_MESSAGE_KIND.items()}

_PB_TO_ATTACHMENT_KIND = {
    pb2.ATTACHMENT_KIND_FILE: AttachmentKind.FILE,
    pb2.ATTACHMENT_KIND_IMAGE: AttachmentKind.IMAGE,
    pb2.ATTACHMENT_KIND_LINK: AttachmentKind.LINK,
}
_ATTACHMENT_KIND_TO_PB = {v: k for k, v in _PB_TO_ATTACHMENT_KIND.items()}


def _participant_to_proto(participant) -> pb2.Participant:  # type: ignore[no-untyped-def]
    return pb2.Participant(
        id=str(participant.id),
        thread_id=str(participant.thread_id),
        role=_PARTICIPANT_ROLE_TO_PB.get(participant.role, pb2.PARTICIPANT_ROLE_UNSPECIFIED),
        display_name=participant.display_name or "",
        metadata=_dict_to_struct(participant.custom_metadata),
        created_at=_timestamp_from_datetime(participant.created_at),
    )


def _attachment_to_proto(attachment) -> pb2.Attachment:  # type: ignore[no-untyped-def]
    return pb2.Attachment(
        id=str(attachment.id),
        message_id=str(attachment.message_id),
        kind=_ATTACHMENT_KIND_TO_PB.get(attachment.kind, pb2.ATTACHMENT_KIND_UNSPECIFIED),
        uri=attachment.uri,
        content_type=attachment.content_type or "",
        metadata=_dict_to_struct(attachment.custom_metadata),
        created_at=_timestamp_from_datetime(attachment.created_at),
    )


def _message_to_proto(message) -> pb2.Message:  # type: ignore[no-untyped-def]
    return pb2.Message(
        id=str(message.id),
        thread_id=str(message.thread_id),
        participant_id=str(message.participant_id or ""),
        kind=_MESSAGE_KIND_TO_PB.get(message.kind, pb2.MESSAGE_KIND_UNSPECIFIED),
        content=message.content,
        metadata=_dict_to_struct(message.custom_metadata),
        created_at=_timestamp_from_datetime(message.created_at),
        attachments=[_attachment_to_proto(att) for att in getattr(message, "attachments", [])],
    )


def _thread_to_proto(thread) -> pb2.Thread:  # type: ignore[no-untyped-def]
    return pb2.Thread(
        id=str(thread.id),
        title=thread.title or "",
        status=_THREAD_STATUS_TO_PB.get(thread.status, pb2.THREAD_STATUS_UNSPECIFIED),
        summary=thread.summary or "",
        metadata=_dict_to_struct(thread.custom_metadata),
        created_at=_timestamp_from_datetime(thread.created_at),
        updated_at=_timestamp_from_datetime(thread.updated_at),
        participants=[_participant_to_proto(p) for p in getattr(thread, "participants", [])],
        messages=[_message_to_proto(m) for m in getattr(thread, "messages", [])],
    )


class ThreadService(pb2_grpc.ThreadServiceServicer):
    """Async gRPC servicer bridging to SQLAlchemy repositories."""

    def __init__(self, session_factory=None):  # type: ignore[no-untyped-def]
        self._session_factory = session_factory or SessionLocal

    async def CreateThread(self, request, context):  # type: ignore[override]
        payload = ThreadCreate(
            title=request.title or None,
            summary=request.summary or None,
            metadata=_struct_to_dict(request.metadata),
            participants=[
                ParticipantCreate(
                    role=_PB_TO_PARTICIPANT_ROLE.get(p.role, ParticipantRole.USER),
                    display_name=p.display_name or None,
                    metadata=_struct_to_dict(p.metadata),
                )
                for p in request.participants
            ],
        )
        async with self._session_factory() as session:
            thread = await create_thread(session, payload)
        return pb2.CreateThreadResponse(thread=_thread_to_proto(thread))

    async def AppendMessage(self, request, context):  # type: ignore[override]
        payload = MessageCreate(
            participant_id=UUID(request.participant_id) if request.participant_id else None,
            kind=_PB_TO_MESSAGE_KIND.get(request.kind, MessageKind.TEXT),
            content=request.content,
            metadata=_struct_to_dict(request.metadata),
            attachments=[
                AttachmentCreate(
                    kind=_PB_TO_ATTACHMENT_KIND.get(att.kind, AttachmentKind.FILE),
                    uri=att.uri,
                    content_type=att.content_type or None,
                    metadata=_struct_to_dict(att.metadata),
                )
                for att in request.attachments
            ],
        )
        try:
            async with self._session_factory() as session:
                message = await append_message(
                    session,
                    thread_id=UUID(request.thread_id),
                    payload=payload,
                )
        except NoResultFound:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Thread not found")
        return pb2.AppendMessageResponse(message=_message_to_proto(message))

    async def GetThread(self, request, context):  # type: ignore[override]
        try:
            async with self._session_factory() as session:
                thread = await get_thread(session, UUID(request.thread_id))
        except NoResultFound:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Thread not found")
        return pb2.GetThreadResponse(thread=_thread_to_proto(thread))

    async def ListThreads(self, request, context):  # type: ignore[override]
        status_filter = _PB_TO_THREAD_STATUS.get(request.status)
        created_after = request.created_after.ToDatetime().replace(tzinfo=timezone.utc) if request.HasField("created_after") else None
        created_before = request.created_before.ToDatetime().replace(tzinfo=timezone.utc) if request.HasField("created_before") else None
        async with self._session_factory() as session:
            threads, total = await list_threads(
                session,
                limit=request.limit or 20,
                offset=request.offset or 0,
                participant_id=UUID(request.participant_id) if request.participant_id else None,
                status=status_filter,
                created_after=created_after,
                created_before=created_before,
            )
        payload = [_thread_to_proto(thread) for thread in threads]
        return pb2.ListThreadsResponse(threads=payload, total=total)

    async def StreamThreadMessages(self, request, context):  # type: ignore[override]
        try:
            async with self._session_factory() as session:
                thread = await get_thread(session, UUID(request.thread_id))
        except NoResultFound:
            await context.abort(grpc.StatusCode.NOT_FOUND, "Thread not found")
        for message in thread.messages:
            yield _message_to_proto(message)


def build_grpc_server() -> grpc.aio.Server:
    """Create a configured gRPC server."""

    server = grpc.aio.server()
    pb2_grpc.add_ThreadServiceServicer_to_server(ThreadService(), server)
    return server


__all__ = ["ThreadService", "build_grpc_server"]
