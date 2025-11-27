"""Pytest configuration and fixtures for thread service tests."""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from thread_service.auth import create_access_token, hash_password
from thread_service.db import Base, get_session
from thread_service.main import create_app
from thread_service.models import (
    AttachmentKind,
    Message,
    MessageAttachment,
    MessageKind,
    Participant,
    ParticipantRole,
    Thread,
    ThreadStatus,
    User,
)
from thread_service.repositories import create_user
from thread_service.settings import Settings


# Test database URL - use environment variable or default to test database
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/thread_service_test",
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Create test database engine and set up schema."""
    # Create test engine
    connect_args = {}
    if "sqlite" in TEST_DATABASE_URL:
        connect_args["check_same_thread"] = False
        poolclass = StaticPool
    else:
        # Use NullPool for PostgreSQL to avoid connection pooling issues in tests
        poolclass = NullPool

    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=poolclass,
        connect_args=connect_args,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with transaction rollback."""
    connection = await test_engine.connect()
    transaction = await connection.begin()

    # Create session bound to the connection
    async_session_maker = async_sessionmaker(
        bind=connection,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    session = async_session_maker()

    yield session

    # Rollback transaction and close
    await session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture
def client(test_session: AsyncSession) -> TestClient:
    """Create a FastAPI test client with database session override."""
    app = create_app()

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield test_session

    app.dependency_overrides[get_session] = override_get_session
    return TestClient(app)


@pytest_asyncio.fixture
async def test_user(test_session: AsyncSession) -> User:
    """Create a test user."""
    user = await create_user(
        test_session,
        email="test@example.com",
        password_hash=hash_password("testpassword123"),
        name="Test User",
    )
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_user2(test_session: AsyncSession) -> User:
    """Create a second test user for isolation testing."""
    user = await create_user(
        test_session,
        email="test2@example.com",
        password_hash=hash_password("testpassword123"),
        name="Test User 2",
    )
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user: User) -> str:
    """Create a JWT token for the test user."""
    return create_access_token(data={"sub": str(test_user.id), "email": test_user.email})


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Create authorization headers for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def authenticated_client(client: TestClient, auth_headers: dict[str, str]) -> TestClient:
    """Create a test client with authentication headers."""
    client.headers.update(auth_headers)
    return client


@pytest_asyncio.fixture
async def test_thread(test_session: AsyncSession, test_user: User) -> Thread:
    """Create a test thread with participants and messages."""
    thread = Thread(
        user_id=test_user.id,
        title="Test Thread",
        status=ThreadStatus.OPEN,
        summary="Test summary",
        custom_metadata={"key": "value"},
    )
    test_session.add(thread)
    await test_session.flush()

    participant = Participant(
        thread_id=thread.id,
        role=ParticipantRole.USER,
        display_name="Test Participant",
        custom_metadata={"role": "user"},
    )
    test_session.add(participant)
    await test_session.flush()

    message = Message(
        thread_id=thread.id,
        participant_id=participant.id,
        kind=MessageKind.TEXT,
        content="Test message content",
        custom_metadata={"message_key": "message_value"},
    )
    test_session.add(message)
    await test_session.flush()

    attachment = MessageAttachment(
        message_id=message.id,
        kind=AttachmentKind.FILE,
        uri="s3://bucket/test-file.txt",
        content_type="text/plain",
        custom_metadata={"attachment_key": "attachment_value"},
    )
    test_session.add(attachment)

    await test_session.commit()
    await test_session.refresh(thread, attribute_names=["participants", "messages"])
    return thread


@pytest_asyncio.fixture
async def test_thread2(test_session: AsyncSession, test_user2: User) -> Thread:
    """Create a second test thread for isolation testing."""
    thread = Thread(
        user_id=test_user2.id,
        title="Test Thread 2",
        status=ThreadStatus.OPEN,
        summary="Test summary 2",
        custom_metadata={"key2": "value2"},
    )
    test_session.add(thread)
    await test_session.commit()
    await test_session.refresh(thread)
    return thread


@pytest_asyncio.fixture
async def multiple_threads(test_session: AsyncSession, test_user: User) -> list[Thread]:
    """Create multiple test threads for pagination and filtering tests."""
    threads = []
    for i in range(5):
        thread = Thread(
            user_id=test_user.id,
            title=f"Test Thread {i}",
            status=ThreadStatus.OPEN if i % 2 == 0 else ThreadStatus.PAUSED,
            summary=f"Test summary {i}",
            custom_metadata={"index": i},
        )
        test_session.add(thread)
        threads.append(thread)

    await test_session.commit()
    for thread in threads:
        await test_session.refresh(thread)
    return threads


@pytest_asyncio.fixture
async def oauth_user(test_session: AsyncSession) -> User:
    """Create a test user without password (OAuth user)."""
    user = await create_user(
        test_session,
        email="oauth@example.com",
        password_hash=None,
        name="OAuth User",
    )
    user.email_verified = True
    await test_session.commit()
    await test_session.refresh(user)
    return user
