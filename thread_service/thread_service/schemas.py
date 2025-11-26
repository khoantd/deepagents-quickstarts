"""Pydantic schemas shared by REST and gRPC layers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .models import AttachmentKind, MessageKind, ParticipantRole, ThreadStatus


class MetadataMixin(BaseModel):
    """Helper mixin that normalizes metadata payloads."""

    metadata: dict[str, Any] = Field(default_factory=dict, alias="custom_metadata")

    model_config = ConfigDict(use_enum_values=True, populate_by_name=True)

    @field_validator("metadata", mode="before")
    @classmethod
    def normalize_metadata(cls, v: Any) -> dict[str, Any]:
        """Normalize metadata from various sources (custom_metadata attribute, MetaData objects, etc.)."""
        # Handle SQLAlchemy MetaData objects
        from sqlalchemy import MetaData as SQLAMetaData
        if isinstance(v, SQLAMetaData):
            return {}
        # Handle None
        if v is None:
            return {}
        # Handle dict
        if isinstance(v, dict):
            return v
        # Try to convert to dict
        try:
            if hasattr(v, "items"):
                return dict(v.items())
            if hasattr(v, "__iter__") and not isinstance(v, (str, bytes)):
                return dict(v)
        except (TypeError, ValueError):
            pass
        return {}


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


class ThreadUpdate(MetadataMixin):
    """Schema for updating thread metadata."""

    title: str | None = None
    summary: str | None = None
    status: ThreadStatus | None = None


class ThreadListResponse(BaseModel):
    threads: list[ThreadRead]
    total: int


class MessageSearchFilters(BaseModel):
    participant_id: UUID | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None


# Authentication schemas
class UserCreate(BaseModel):
    email: str
    password: str
    name: str | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None = None
    avatar_url: str | None = None
    email_verified: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    name: str | None = None
    avatar_url: str | None = None


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


class EmailVerificationRequest(BaseModel):
    token: str


class OAuthUserInfo(BaseModel):
    """OAuth user information from NextAuth."""
    provider: str
    provider_user_id: str
    email: str
    name: str | None = None
    avatar_url: str | None = None
