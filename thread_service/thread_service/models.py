"""SQLAlchemy models representing thread data."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, String, Text, TypeDecorator, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class ThreadStatus(str, Enum):
    """Enumeration of available thread lifecycle states."""

    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        """Pydantic v2 schema generator for ThreadStatus enum."""
        from pydantic_core import core_schema

        # Get enum values - use _member_map_ which is available even during class definition
        if hasattr(cls, '_member_map_'):
            values = [member.value for member in cls._member_map_.values()]
        else:
            # Fallback: use hardcoded values
            values = ["open", "paused", "closed"]
        return core_schema.literal_schema(values)


class ThreadStatusType(TypeDecorator):
    """Custom type to handle ThreadStatus enum with database enum values."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert enum to database value."""
        if value is None:
            return None
        if isinstance(value, ThreadStatus):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        """Convert database value to enum."""
        if value is None:
            return None
        if isinstance(value, str):
            # Map string value to enum
            try:
                return ThreadStatus(value)
            except ValueError:
                # Fallback: try case-insensitive match
                for status in ThreadStatus:
                    if status.value.lower() == value.lower():
                        return status
                raise ValueError(f"Invalid thread status: {value}")
        return value


class ParticipantRole(str, Enum):
    """Identifies a participant's role within a conversation."""

    USER = "user"
    AGENT = "agent"
    TOOL = "tool"

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        """Pydantic v2 schema generator for ParticipantRole enum."""
        from pydantic_core import core_schema

        # Get enum values - use _member_map_ which is available even during class definition
        if hasattr(cls, '_member_map_'):
            values = [member.value for member in cls._member_map_.values()]
        else:
            # Fallback: use hardcoded values
            values = ["user", "agent", "tool"]
        return core_schema.literal_schema(values)


class ParticipantRoleType(TypeDecorator):
    """Custom type to handle ParticipantRole enum with database enum values."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert enum to database value."""
        if value is None:
            return None
        if isinstance(value, ParticipantRole):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        """Convert database value to enum."""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return ParticipantRole(value)
            except ValueError:
                for role in ParticipantRole:
                    if role.value.lower() == value.lower():
                        return role
                raise ValueError(f"Invalid participant role: {value}")
        return value


class MessageKind(str, Enum):
    """Classifies message semantics for filtering/analytics."""

    TEXT = "text"
    RICH = "rich"
    TOOL_CALL = "tool_call"

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        """Pydantic v2 schema generator for MessageKind enum."""
        from pydantic_core import core_schema

        # Get enum values - use _member_map_ which is available even during class definition
        if hasattr(cls, '_member_map_'):
            values = [member.value for member in cls._member_map_.values()]
        else:
            # Fallback: use hardcoded values
            values = ["text", "rich", "tool_call"]
        return core_schema.literal_schema(values)


class MessageKindType(TypeDecorator):
    """Custom type to handle MessageKind enum with database enum values."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert enum to database value."""
        if value is None:
            return None
        if isinstance(value, MessageKind):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        """Convert database value to enum."""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return MessageKind(value)
            except ValueError:
                for kind in MessageKind:
                    if kind.value.lower() == value.lower():
                        return kind
                raise ValueError(f"Invalid message kind: {value}")
        return value


class AttachmentKind(str, Enum):
    """Attachment payload types."""

    FILE = "file"
    IMAGE = "image"
    LINK = "link"

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        """Pydantic v2 schema generator for AttachmentKind enum."""
        from pydantic_core import core_schema

        # Get enum values - use _member_map_ which is available even during class definition
        if hasattr(cls, '_member_map_'):
            values = [member.value for member in cls._member_map_.values()]
        else:
            # Fallback: use hardcoded values
            values = ["file", "image", "link"]
        return core_schema.literal_schema(values)


class AttachmentKindType(TypeDecorator):
    """Custom type to handle AttachmentKind enum with database enum values."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert enum to database value."""
        if value is None:
            return None
        if isinstance(value, AttachmentKind):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        """Convert database value to enum."""
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return AttachmentKind(value)
            except ValueError:
                for kind in AttachmentKind:
                    if kind.value.lower() == value.lower():
                        return kind
                raise ValueError(f"Invalid attachment kind: {value}")
        return value


class User(Base):
    """User account information."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    threads: Mapped[list["Thread"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    oauth_accounts: Mapped[list["OAuthAccount"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class OAuthAccount(Base):
    """OAuth provider account links."""

    __tablename__ = "oauth_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="oauth_accounts")

    __table_args__ = (
        Index("ix_oauth_accounts_provider_user", "provider", "provider_user_id", unique=True),
    )


class EmailVerificationToken(Base):
    """Email verification tokens."""

    __tablename__ = "email_verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class PasswordResetToken(Base):
    """Password reset tokens."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Thread(Base):
    """Top-level thread metadata."""

    __tablename__ = "threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ThreadStatus] = mapped_column(
        ThreadStatusType(),
        default=ThreadStatus.OPEN,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="threads")
    participants: Mapped[list["Participant"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list["Message"]] = relationship(
        back_populates="thread",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Participant(Base):
    """Individuals or agents taking part in a thread."""

    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[ParticipantRole] = mapped_column(
        ParticipantRoleType(),
        default=ParticipantRole.USER,
    )
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custom_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    thread: Mapped[Thread] = relationship(back_populates="participants")
    messages: Mapped[list["Message"]] = relationship(back_populates="participant")


class Message(Base):
    """Individual conversational messages."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("threads.id", ondelete="CASCADE"),
        nullable=False,
    )
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind: Mapped[MessageKind] = mapped_column(
        MessageKindType(),
        default=MessageKind.TEXT,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    custom_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    thread: Mapped[Thread] = relationship(back_populates="messages")
    participant: Mapped[Participant | None] = relationship(back_populates="messages")
    attachments: Mapped[list["MessageAttachment"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
    )


class MessageAttachment(Base):
    """Optional attachment metadata for a message."""

    __tablename__ = "message_attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[AttachmentKind] = mapped_column(
        AttachmentKindType(),
        default=AttachmentKind.FILE,
    )
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    custom_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    message: Mapped[Message] = relationship(back_populates="attachments")


__all__ = [
    "AttachmentKind",
    "EmailVerificationToken",
    "Message",
    "MessageAttachment",
    "MessageKind",
    "OAuthAccount",
    "Participant",
    "ParticipantRole",
    "PasswordResetToken",
    "Thread",
    "ThreadStatus",
    "User",
]
