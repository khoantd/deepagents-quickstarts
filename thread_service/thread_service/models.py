"""SQLAlchemy models representing thread data."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class ThreadStatus(str, Enum):
    """Enumeration of available thread lifecycle states."""

    OPEN = "open"
    PAUSED = "paused"
    CLOSED = "closed"


class ParticipantRole(str, Enum):
    """Identifies a participant's role within a conversation."""

    USER = "user"
    AGENT = "agent"
    TOOL = "tool"


class MessageKind(str, Enum):
    """Classifies message semantics for filtering/analytics."""

    TEXT = "text"
    RICH = "rich"
    TOOL_CALL = "tool_call"


class AttachmentKind(str, Enum):
    """Attachment payload types."""

    FILE = "file"
    IMAGE = "image"
    LINK = "link"


class Thread(Base):
    """Top-level thread metadata."""

    __tablename__ = "threads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ThreadStatus] = mapped_column(default=ThreadStatus.OPEN)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
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
    role: Mapped[ParticipantRole] = mapped_column(default=ParticipantRole.USER)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
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
    kind: Mapped[MessageKind] = mapped_column(default=MessageKind.TEXT)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
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
    kind: Mapped[AttachmentKind] = mapped_column(default=AttachmentKind.FILE)
    uri: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    message: Mapped[Message] = relationship(back_populates="attachments")


__all__ = [
    "AttachmentKind",
    "Message",
    "MessageAttachment",
    "MessageKind",
    "Participant",
    "ParticipantRole",
    "Thread",
    "ThreadStatus",
]
