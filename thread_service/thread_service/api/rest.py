"""REST API router for managing threads."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound

from ..db import get_session
from ..middleware import get_current_user
from ..models import ThreadStatus, User
from ..repositories import append_message, create_thread, get_thread, list_threads
from ..schemas import MessageCreate, MessageRead, ThreadCreate, ThreadListResponse, ThreadRead

router = APIRouter(prefix="/threads", tags=["Threads"])


def _normalize_metadata(obj: Any) -> dict[str, Any]:
    """Convert metadata to a dict, handling SQLAlchemy JSONB types and MetaData objects."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    # Handle SQLAlchemy MetaData objects - check if it's actually SQLAlchemy's MetaData class
    from sqlalchemy import MetaData as SQLAMetaData
    if isinstance(obj, SQLAMetaData):
        # This shouldn't happen, but if it does, return empty dict
        return {}
    # Handle SQLAlchemy JSONB types or other objects that can be converted to dict
    try:
        if hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes)):
            # Try to convert to dict
            if hasattr(obj, "items"):
                return dict(obj.items())
            # Try list of tuples
            return dict(obj)
    except (TypeError, ValueError):
        pass
    # If all else fails, return empty dict
    return {}


@router.post("", response_model=ThreadRead, status_code=status.HTTP_201_CREATED)
async def create_thread_endpoint(
    payload: ThreadCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ThreadRead:
    """Create a new thread with optional participants."""

    thread = await create_thread(session, payload, user_id=current_user.id)
    
    # Normalize metadata fields before validation
    if hasattr(thread, "custom_metadata"):
        thread.custom_metadata = _normalize_metadata(thread.custom_metadata)
    if hasattr(thread, "participants"):
        for participant in thread.participants:
            if hasattr(participant, "custom_metadata"):
                participant.custom_metadata = _normalize_metadata(participant.custom_metadata)
    
    return ThreadRead.model_validate(thread, from_attributes=True)


@router.get("", response_model=ThreadListResponse)
async def list_threads_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    participant_id: UUID | None = None,
    status_filter: ThreadStatus | None = Query(default=None, alias="status"),
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> ThreadListResponse:
    """List threads with optional filters (user-scoped)."""
    import logging

    logger = logging.getLogger(__name__)

    try:
        threads, total = await list_threads(
            session,
            user_id=current_user.id,
            limit=limit,
            offset=offset,
            participant_id=participant_id,
            status=status_filter,
            created_after=created_after,
            created_before=created_before,
        )
        # Normalize metadata fields before validation
        # The issue is that custom_metadata might be returning SQLAlchemy MetaData objects
        # We need to ensure they're converted to dicts before Pydantic validation
        normalized_threads = []
        for thread in threads:
            # Normalize thread metadata - use getattr with safe default
            try:
                meta_value = getattr(thread, "custom_metadata", {})
                # Check if it's a SQLAlchemy MetaData object
                from sqlalchemy import MetaData as SQLAMetaData
                if isinstance(meta_value, SQLAMetaData):
                    logger.warning("Thread %s has MetaData object instead of dict, converting to empty dict", thread.id)
                    meta_value = {}
                else:
                    meta_value = _normalize_metadata(meta_value)
                setattr(thread, "custom_metadata", meta_value)
            except Exception as e:
                logger.warning("Failed to normalize thread metadata for %s: %s", getattr(thread, "id", "unknown"), e)
                setattr(thread, "custom_metadata", {})
            
            # Normalize participant metadata
            if hasattr(thread, "participants") and thread.participants:
                for participant in thread.participants:
                    try:
                        meta_value = getattr(participant, "custom_metadata", {})
                        from sqlalchemy import MetaData as SQLAMetaData
                        if isinstance(meta_value, SQLAMetaData):
                            meta_value = {}
                        else:
                            meta_value = _normalize_metadata(meta_value)
                        setattr(participant, "custom_metadata", meta_value)
                    except Exception as e:
                        logger.warning("Failed to normalize participant metadata: %s", e)
                        setattr(participant, "custom_metadata", {})
            
            # Normalize message metadata
            if hasattr(thread, "messages") and thread.messages:
                for message in thread.messages:
                    try:
                        meta_value = getattr(message, "custom_metadata", {})
                        from sqlalchemy import MetaData as SQLAMetaData
                        if isinstance(meta_value, SQLAMetaData):
                            meta_value = {}
                        else:
                            meta_value = _normalize_metadata(meta_value)
                        setattr(message, "custom_metadata", meta_value)
                    except Exception as e:
                        logger.warning("Failed to normalize message metadata: %s", e)
                        setattr(message, "custom_metadata", {})
                    
                    # Normalize attachment metadata
                    if hasattr(message, "attachments") and message.attachments:
                        for attachment in message.attachments:
                            try:
                                meta_value = getattr(attachment, "custom_metadata", {})
                                from sqlalchemy import MetaData as SQLAMetaData
                                if isinstance(meta_value, SQLAMetaData):
                                    meta_value = {}
                                else:
                                    meta_value = _normalize_metadata(meta_value)
                                setattr(attachment, "custom_metadata", meta_value)
                            except Exception as e:
                                logger.warning("Failed to normalize attachment metadata: %s", e)
                                setattr(attachment, "custom_metadata", {})
            
            normalized_threads.append(thread)
        
        payload = [ThreadRead.model_validate(t, from_attributes=True) for t in normalized_threads]
        return ThreadListResponse(threads=payload, total=total)
    except Exception as e:
        logger.exception("Error listing threads for user %s: %s", current_user.id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list threads: {str(e)}",
        ) from e


@router.get("/{thread_id}", response_model=ThreadRead)
async def get_thread_endpoint(
    thread_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ThreadRead:
    """Return a single thread by identifier (user-scoped)."""

    try:
        thread = await get_thread(session, thread_id, user_id=current_user.id)
    except NoResultFound as exc:  # pragma: no cover - FastAPI handles detail
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found") from exc
    
    # Normalize metadata fields before validation
    if hasattr(thread, "custom_metadata"):
        thread.custom_metadata = _normalize_metadata(thread.custom_metadata)
    if hasattr(thread, "participants"):
        for participant in thread.participants:
            if hasattr(participant, "custom_metadata"):
                participant.custom_metadata = _normalize_metadata(participant.custom_metadata)
    if hasattr(thread, "messages"):
        for message in thread.messages:
            if hasattr(message, "custom_metadata"):
                message.custom_metadata = _normalize_metadata(message.custom_metadata)
            if hasattr(message, "attachments"):
                for attachment in message.attachments:
                    if hasattr(attachment, "custom_metadata"):
                        attachment.custom_metadata = _normalize_metadata(attachment.custom_metadata)
    
    return ThreadRead.model_validate(thread, from_attributes=True)


@router.post("/{thread_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def append_message_endpoint(
    thread_id: UUID,
    payload: MessageCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MessageRead:
    """Append a message to an existing thread (user-scoped)."""

    # Verify thread ownership
    try:
        await get_thread(session, thread_id, user_id=current_user.id)
    except NoResultFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found") from exc

    try:
        message = await append_message(session, thread_id=thread_id, payload=payload)
    except NoResultFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found") from exc
    
    # Normalize metadata fields before validation
    if hasattr(message, "custom_metadata"):
        message.custom_metadata = _normalize_metadata(message.custom_metadata)
    if hasattr(message, "attachments"):
        for attachment in message.attachments:
            if hasattr(attachment, "custom_metadata"):
                attachment.custom_metadata = _normalize_metadata(attachment.custom_metadata)
    
    return MessageRead.model_validate(message, from_attributes=True)
