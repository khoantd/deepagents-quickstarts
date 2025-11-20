"""Data-access helpers shared between API layers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    EmailVerificationToken,
    Message,
    MessageAttachment,
    OAuthAccount,
    Participant,
    PasswordResetToken,
    Thread,
    ThreadStatus,
    User,
)
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


# User repository functions
async def create_user(
    session: AsyncSession,
    *,
    email: str,
    password_hash: str | None = None,
    name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    """Create a new user account.

    Args:
        session: Database session
        email: User email address
        password_hash: Hashed password (None for OAuth users)
        name: User display name
        avatar_url: User avatar URL

    Returns:
        Created User instance
    """
    user = User(
        email=email,
        password_hash=password_hash,
        name=name,
        avatar_url=avatar_url,
        email_verified=False,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    """Get a user by email address.

    Args:
        session: Database session
        email: User email address

    Returns:
        User instance if found, None otherwise
    """
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_by_id(session: AsyncSession, user_id: UUID) -> User | None:
    """Get a user by ID.

    Args:
        session: Database session
        user_id: User UUID

    Returns:
        User instance if found, None otherwise
    """
    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def verify_user_email(session: AsyncSession, user_id: UUID) -> User:
    """Mark a user's email as verified.

    Args:
        session: Database session
        user_id: User UUID

    Returns:
        Updated User instance

    Raises:
        NoResultFound: If user doesn't exist
    """
    user = await get_user_by_id(session, user_id)
    if not user:
        raise NoResultFound
    user.email_verified = True
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_password(session: AsyncSession, user_id: UUID, password_hash: str) -> User:
    """Update a user's password.

    Args:
        session: Database session
        user_id: User UUID
        password_hash: New hashed password

    Returns:
        Updated User instance

    Raises:
        NoResultFound: If user doesn't exist
    """
    user = await get_user_by_id(session, user_id)
    if not user:
        raise NoResultFound
    user.password_hash = password_hash
    await session.commit()
    await session.refresh(user)
    return user


async def create_oauth_account(
    session: AsyncSession,
    *,
    user_id: UUID,
    provider: str,
    provider_user_id: str,
    access_token: str | None = None,
    refresh_token: str | None = None,
    expires_at: datetime | None = None,
) -> OAuthAccount:
    """Create or update an OAuth account link.

    Args:
        session: Database session
        user_id: User UUID
        provider: OAuth provider name (e.g., 'google', 'github')
        provider_user_id: Provider's user ID
        access_token: OAuth access token
        refresh_token: OAuth refresh token
        expires_at: Token expiration time

    Returns:
        Created or updated OAuthAccount instance
    """
    # Check if account already exists
    stmt = select(OAuthAccount).where(
        OAuthAccount.provider == provider,
        OAuthAccount.provider_user_id == provider_user_id,
    )
    result = await session.execute(stmt)
    oauth_account = result.scalar_one_or_none()

    if oauth_account:
        # Update existing account
        oauth_account.access_token = access_token
        oauth_account.refresh_token = refresh_token
        oauth_account.expires_at = expires_at
    else:
        # Create new account
        oauth_account = OAuthAccount(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )
        session.add(oauth_account)

    await session.commit()
    await session.refresh(oauth_account)
    return oauth_account


async def get_oauth_account(
    session: AsyncSession,
    *,
    provider: str,
    provider_user_id: str,
) -> OAuthAccount | None:
    """Get an OAuth account by provider and provider user ID.

    Args:
        session: Database session
        provider: OAuth provider name
        provider_user_id: Provider's user ID

    Returns:
        OAuthAccount instance if found, None otherwise
    """
    stmt = select(OAuthAccount).where(
        OAuthAccount.provider == provider,
        OAuthAccount.provider_user_id == provider_user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_email_verification_token(
    session: AsyncSession,
    *,
    user_id: UUID,
    token: str,
    expires_at: datetime,
) -> EmailVerificationToken:
    """Create an email verification token.

    Args:
        session: Database session
        user_id: User UUID
        token: Verification token string
        expires_at: Token expiration time

    Returns:
        Created EmailVerificationToken instance
    """
    verification_token = EmailVerificationToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
    )
    session.add(verification_token)
    await session.commit()
    await session.refresh(verification_token)
    return verification_token


async def verify_email_token(session: AsyncSession, token: str) -> EmailVerificationToken | None:
    """Verify and retrieve an email verification token.

    Args:
        session: Database session
        token: Verification token string

    Returns:
        EmailVerificationToken instance if valid, None otherwise
    """
    stmt = select(EmailVerificationToken).where(
        EmailVerificationToken.token == token,
        EmailVerificationToken.expires_at > datetime.now(),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_password_reset_token(
    session: AsyncSession,
    *,
    user_id: UUID,
    token: str,
    expires_at: datetime,
) -> PasswordResetToken:
    """Create a password reset token.

    Args:
        session: Database session
        user_id: User UUID
        token: Reset token string
        expires_at: Token expiration time

    Returns:
        Created PasswordResetToken instance
    """
    reset_token = PasswordResetToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
    )
    session.add(reset_token)
    await session.commit()
    await session.refresh(reset_token)
    return reset_token


async def verify_password_reset_token(
    session: AsyncSession,
    token: str,
) -> PasswordResetToken | None:
    """Verify and retrieve a password reset token.

    Args:
        session: Database session
        token: Reset token string

    Returns:
        PasswordResetToken instance if valid, None otherwise
    """
    stmt = select(PasswordResetToken).where(
        PasswordResetToken.token == token,
        PasswordResetToken.expires_at > datetime.now(),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def delete_password_reset_token(session: AsyncSession, token: str) -> None:
    """Delete a password reset token after use.

    Args:
        session: Database session
        token: Reset token string
    """
    stmt = select(PasswordResetToken).where(PasswordResetToken.token == token)
    result = await session.execute(stmt)
    reset_token = result.scalar_one_or_none()
    if reset_token:
        await session.delete(reset_token)
        await session.commit()


# Thread repository functions (updated to require user_id)
async def create_thread(
    session: AsyncSession,
    payload: ThreadCreate,
    user_id: UUID,
) -> Thread:
    """Persist a new thread along with its participants.

    Args:
        session: Database session
        payload: Thread creation data
        user_id: User ID who owns the thread

    Returns:
        Created Thread instance
    """
    thread = Thread(
        user_id=user_id,
        title=payload.title,
        summary=payload.summary,
        status=payload.status,
        custom_metadata=payload.metadata,
    )
    session.add(thread)
    await session.flush()

    for participant in payload.participants:
        session.add(
            Participant(
                thread_id=thread.id,
                role=participant.role,
                display_name=participant.display_name,
                custom_metadata=participant.metadata,
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
    user_id: UUID,
    limit: int,
    offset: int,
    participant_id: UUID | None,
    status: ThreadStatus | None,
    created_after: datetime | None,
    created_before: datetime | None,
) -> tuple[list[Thread], int]:
    """Return paginated threads and a total count for a specific user.

    Args:
        session: Database session
        user_id: User ID to filter threads by
        limit: Maximum number of threads to return
        offset: Number of threads to skip
        participant_id: Optional participant ID filter
        status: Optional status filter
        created_after: Optional created after date filter
        created_before: Optional created before date filter

    Returns:
        Tuple of (list of threads, total count)
    """
    base_stmt = (
        select(Thread)
        .options(
            selectinload(Thread.participants),
            selectinload(Thread.messages).selectinload(Message.attachments),
        )
        .where(Thread.user_id == user_id)
        .order_by(Thread.created_at.desc())
    )

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
        select(func.count(Thread.id)).where(Thread.user_id == user_id),
        participant_id=participant_id,
        status=status,
        created_after=created_after,
        created_before=created_before,
    )
    total = await session.scalar(count_stmt) or 0
    return threads, int(total)


async def get_thread(session: AsyncSession, thread_id: UUID, user_id: UUID) -> Thread:
    """Fetch a thread with relationships or raise if absent.

    Args:
        session: Database session
        thread_id: Thread UUID
        user_id: User UUID (must own the thread)

    Returns:
        Thread instance

    Raises:
        NoResultFound: If thread doesn't exist or user doesn't own it
    """
    stmt = (
        select(Thread)
        .options(
            selectinload(Thread.participants),
            selectinload(Thread.messages).selectinload(Message.attachments),
        )
        .where(Thread.id == thread_id, Thread.user_id == user_id)
    )
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
        custom_metadata=payload.metadata,
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
                custom_metadata=attachment.metadata,
            )
        )

    await session.commit()
    await session.refresh(message, attribute_names=["attachments"])
    return message
