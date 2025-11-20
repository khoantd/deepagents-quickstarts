"""Data-access helpers shared between API layers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Message, Participant, Thread, ThreadStatus
from .schemas import AttachmentCreate, MessageCreate, ThreadCreate


def _apply_filters(
    stmt: Select[tuple[Thread]],
    *,
    participant_id: UUID | None,
    status: ThreadStatus | None,
    created_after: datetime | None,
    created_before: datetime | None,
) -> Select[tuple[Thread]]:
    if participant_id:
        stmt = stmt.join(Thread.participants).where(Participant.id == participant_id)
    if status:
        stmt = stmt.where(Thread.status == status)
    if created_after:
        stmt = stmt.where(Thread.created_at >= created_after)
    if created_before:
        stmt = stmt.where(Thread.created_at <= created_before)
    return stmt


async def create_thread(session: AsyncSession, payload: ThreadCreate) -> Thread:
    """Persist a new thread along with its participants."""

    thread = Thread(
        title=payload.title,
        summary=payload.summary,
        status=payload.status,
        metadata=payload.metadata,
    )
    session.add(thread)
    await session.flush()

    for participant in payload.participants:
        session.add(
            Participant(
                thread_id=thread.id,
                role=participant.role,
                display_name=participant.display_name,
                metadata=participant.metadata,
            )
        )

    await session.commit()
    await session.refresh(
        thread,
        attribute_names=["participants", "messages"],
    )
    return thread


async def list_threads(
    session: AsyncSession,
    *,
    limit: int,
    offset: int,
    participant_id: UUID | None,
    status: ThreadStatus | None,
    created_after: datetime | None,
    created_before: datetime | None,
) -> tuple[list[Thread], int]:
    """Return paginated threads and a total count."""

    base_stmt = select(Thread).options(
        selectinload(Thread.participants),
        selectinload(Thread.messages).selectinload(Message.attachments),
    ).order_by(Thread.created_at.desc())

    filtered_stmt = _apply_filters(
        base_stmt,
        participant_id=participant_id,
        status=status,
        created_after=created_after,
        created_before=created_before,
    )

    rows = await session.execute(filtered_stmt.limit(limit).offset(offset))
    threads = list(rows.scalars().unique().all())

    count_stmt = _apply_filters(
        select(func.count(Thread.id)),
        participant_id=participant_id,
        status=status,
        created_after=created_after,
        created_before=created_before,
    )
    total = await session.scalar(count_stmt) or 0
    return threads, int(total)


async def get_thread(session: AsyncSession, thread_id: UUID) -> Thread:
    """Fetch a thread with relationships or raise if absent."""

    stmt = select(Thread).options(
        selectinload(Thread.participants),
        selectinload(Thread.messages).selectinload(Message.attachments),
    ).where(Thread.id == thread_id)
    result = await session.execute(stmt)
    thread = result.scalars().unique().one_or_none()
    if not thread:
        raise NoResultFound
    return thread


async def append_message(
    session: AsyncSession,
    *,
    thread_id: UUID,
    payload: MessageCreate,
) -> Message:
    """Append a new message to an existing thread."""

    result = await session.scalar(select(Thread.id).where(Thread.id == thread_id))
    if not result:
        raise NoResultFound

    message = Message(
        thread_id=thread_id,
        participant_id=payload.participant_id,
        kind=payload.kind,
        content=payload.content,
        metadata=payload.metadata,
    )
    session.add(message)
    await session.flush()

    for attachment in payload.attachments:
        session.add(
            MessageAttachment(
                message_id=message.id,
                kind=attachment.kind,
                uri=attachment.uri,
                content_type=attachment.content_type,
                metadata=attachment.metadata,
            )
        )

    await session.commit()
    await session.refresh(message, attribute_names=["attachments"])
    return message
