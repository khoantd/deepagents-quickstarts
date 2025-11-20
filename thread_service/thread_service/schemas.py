"""Pydantic schemas shared by REST and gRPC layers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .models import AttachmentKind, MessageKind, ParticipantRole, ThreadStatus


class MetadataMixin(BaseModel):
    """Helper mixin that normalizes metadata payloads."""

    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


class ParticipantCreate(MetadataMixin):
    role: ParticipantRole = ParticipantRole.USER
    display_name: str | None = None


class ParticipantRead(MetadataMixin):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID
    thread_id: UUID
    role: ParticipantRole
    display_name: str | None = None
    created_at: datetime


class AttachmentCreate(MetadataMixin):
    kind: AttachmentKind = AttachmentKind.FILE
    uri: str
    content_type: str | None = None


class AttachmentRead(MetadataMixin):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID
    message_id: UUID
    kind: AttachmentKind
    uri: str
    content_type: str | None = None
    created_at: datetime


class MessageCreate(MetadataMixin):
    participant_id: UUID | None = None
    kind: MessageKind = MessageKind.TEXT
    content: str
    attachments: list[AttachmentCreate] = Field(default_factory=list)


class MessageRead(MetadataMixin):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID
    thread_id: UUID
    participant_id: UUID | None
    kind: MessageKind
    content: str
    created_at: datetime
    attachments: list[AttachmentRead] = Field(default_factory=list)


class ThreadCreate(MetadataMixin):
    title: str | None = None
    summary: str | None = None
    status: ThreadStatus = ThreadStatus.OPEN
    participants: list[ParticipantCreate] = Field(default_factory=list)


class ThreadRead(MetadataMixin):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID
    title: str | None = None
    status: ThreadStatus
    summary: str | None = None
    created_at: datetime
    updated_at: datetime
    participants: list[ParticipantRead] = Field(default_factory=list)
    messages: list[MessageRead] = Field(default_factory=list)


class ThreadListResponse(BaseModel):
    threads: list[ThreadRead]
    total: int


class MessageSearchFilters(BaseModel):
    participant_id: UUID | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
