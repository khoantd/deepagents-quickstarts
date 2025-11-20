"""REST API router for managing threads."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from ..db import get_session
from ..models import ThreadStatus
from ..repositories import append_message, create_thread, get_thread, list_threads
from ..schemas import MessageCreate, MessageRead, ThreadCreate, ThreadListResponse, ThreadRead

router = APIRouter(prefix="/threads", tags=["Threads"])


@router.post("", response_model=ThreadRead, status_code=status.HTTP_201_CREATED)
async def create_thread_endpoint(
    payload: ThreadCreate,
    session: AsyncSession = Depends(get_session),
) -> ThreadRead:
    """Create a new thread with optional participants."""

    thread = await create_thread(session, payload)
    return ThreadRead.model_validate(thread, from_attributes=True)


@router.get("", response_model=ThreadListResponse)
async def list_threads_endpoint(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    participant_id: UUID | None = None,
    status_filter: ThreadStatus | None = Query(default=None, alias="status"),
    created_after: datetime | None = None,
    created_before: datetime | None = None,
    session: AsyncSession = Depends(get_session),
) -> ThreadListResponse:
    """List threads with optional filters."""

    threads, total = await list_threads(
        session,
        limit=limit,
        offset=offset,
        participant_id=participant_id,
        status=status_filter,
        created_after=created_after,
        created_before=created_before,
    )
    payload = [ThreadRead.model_validate(t, from_attributes=True) for t in threads]
    return ThreadListResponse(threads=payload, total=total)


@router.get("/{thread_id}", response_model=ThreadRead)
async def get_thread_endpoint(
    thread_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> ThreadRead:
    """Return a single thread by identifier."""

    try:
        thread = await get_thread(session, thread_id)
    except NoResultFound as exc:  # pragma: no cover - FastAPI handles detail
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found") from exc
    return ThreadRead.model_validate(thread, from_attributes=True)


@router.post("/{thread_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def append_message_endpoint(
    thread_id: UUID,
    payload: MessageCreate,
    session: AsyncSession = Depends(get_session),
) -> MessageRead:
    """Append a message to an existing thread."""

    try:
        message = await append_message(session, thread_id=thread_id, payload=payload)
    except NoResultFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found") from exc
    return MessageRead.model_validate(message, from_attributes=True)
