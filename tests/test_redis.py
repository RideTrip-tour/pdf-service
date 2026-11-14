import asyncio
from unittest.mock import MagicMock

import fakeredis
import pytest

from app.redis.tasks import generate_pdf_task


def test_generate_pdf_task_publishes_to_redis_on_success(monkeypatch):
    request_data = {
        "request_id": "task-1",
        "user_id": 1,
        "payload": {"route": {"from_place": "A", "to_place": "B"}},
    }

    monkeypatch.setattr("app.redis.tasks.process_message", MagicMock())

    mock_session = MagicMock()
    monkeypatch.setattr(
        "app.redis.tasks.SessionLocal", MagicMock(return_value=mock_session)
    )

    mock_publish = MagicMock()
    monkeypatch.setattr("app.redis.tasks.sync_redis.publish", mock_publish)

    generate_pdf_task(request_data)

    mock_publish.assert_called_once()
    args, _ = mock_publish.call_args
    assert "task_updates:task-1" in args[0]
    assert '"status": "ready"' in args[1]


def test_generate_pdf_task_publishes_failed_on_error(monkeypatch):
    request_data = {
        "request_id": "task-2",
        "user_id": 1,
        "payload": {"route": {"from_place": "A", "to_place": "B"}},
    }

    monkeypatch.setattr(
        "app.redis.tasks.process_message",
        MagicMock(side_effect=Exception("Render error")),
    )
    monkeypatch.setattr("app.redis.tasks.SessionLocal", MagicMock())

    mock_publish = MagicMock()
    monkeypatch.setattr("app.redis.tasks.sync_redis.publish", mock_publish)

    from celery.exceptions import Retry

    try:
        generate_pdf_task(request_data)
    except Retry:
        pass

    mock_publish.assert_called_once()
    args, _ = mock_publish.call_args
    assert "task_updates:task-2" in args[0]
    assert '"status": "failed"' in args[1]


@pytest.mark.asyncio
async def test_redis_pubsub_roundtrip():
    server = fakeredis.FakeServer()
    async_redis = fakeredis.FakeAsyncRedis(server=server, decode_responses=True)
    sync_redis = fakeredis.FakeRedis(server=server, decode_responses=True)

    pubsub = async_redis.pubsub()
    await pubsub.subscribe("test_channel")

    subscribers_count = sync_redis.publish("test_channel", '{"status": "ready"}')
    assert subscribers_count == 1

    await asyncio.sleep(0.1)

    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if message:
            break

    assert message is not None
    assert message["data"] == '{"status": "ready"}'

    await pubsub.close()
