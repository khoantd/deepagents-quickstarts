from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from thread_service.api import rest
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
)


@pytest.fixture()
def client(monkeypatch):
    app = create_app()

    async def _session_override():
        yield None

    app.dependency_overrides[rest.get_session] = _session_override  # type: ignore[attr-defined]
    return TestClient(app)


def _sample_thread():
    thread_id = uuid4()
    participant_id = uuid4()
    message_id = uuid4()
    attachment_id = uuid4()
    now = datetime.now(timezone.utc)

    participant = Participant(
        id=participant_id,
        thread_id=thread_id,
        role=ParticipantRole.USER,
        display_name="User",
        metadata={},
        created_at=now,
    )
    attachment = MessageAttachment(
        id=attachment_id,
        message_id=message_id,
        kind=AttachmentKind.FILE,
        uri="s3://bucket/file.txt",
        content_type="text/plain",
        metadata={},
        created_at=now,
    )
    message = Message(
        id=message_id,
        thread_id=thread_id,
        participant_id=participant_id,
        kind=MessageKind.TEXT,
        content="hello",
        metadata={},
        created_at=now,
    )
    message.attachments = [attachment]

    thread = Thread(
        id=thread_id,
        title="Demo thread",
        status=ThreadStatus.OPEN,
        summary=None,
        metadata={},
        created_at=now,
        updated_at=now,
    )
    thread.participants = [participant]
    thread.messages = [message]
    return thread


def test_health_endpoint(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_thread_endpoint(client, monkeypatch):
    sample = _sample_thread()

    async def _fake_create_thread(session, payload):  # noqa: ARG001
        return sample

    monkeypatch.setattr(rest, "create_thread", _fake_create_thread)

    response = client.post(
        "/threads",
        json={"title": "Demo", "participants": [{"role": "user"}]},
    )
    assert response.status_code == 201
    assert response.json()["id"] == str(sample.id)


def test_list_threads_endpoint(client, monkeypatch):
    sample = _sample_thread()

    async def _fake_list_threads(session, **kwargs):  # noqa: ARG001
        return [sample], 1

    monkeypatch.setattr(rest, "list_threads", _fake_list_threads)

    response = client.get("/threads?limit=5")
    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 1
    assert len(body["threads"]) == 1


def test_get_thread_endpoint(client, monkeypatch):
    sample = _sample_thread()

    async def _fake_get_thread(session, thread_id):  # noqa: ARG001
        return sample

    monkeypatch.setattr(rest, "get_thread", _fake_get_thread)

    response = client.get(f"/threads/{sample.id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Demo thread"


def test_append_message_endpoint(client, monkeypatch):
    sample = _sample_thread().messages[0]

    async def _fake_append_message(session, thread_id, payload):  # noqa: ARG001
        return sample

    monkeypatch.setattr(rest, "append_message", _fake_append_message)

    response = client.post(
        f"/threads/{sample.thread_id}/messages",
        json={"content": "Hi", "attachments": []},
    )
    assert response.status_code == 201
    assert response.json()["id"] == str(sample.id)
