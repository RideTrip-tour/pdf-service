import json
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.broker.tasks import generate_pdf_task
from app.exceptions import PermanentError
from app.publishers.event_consumer import EventConsumer


def test_generate_pdf_task_publishes_to_redis_on_success(monkeypatch):
    request_data = {
        "request_id": "task-1",
        "user_id": 1,
        "payload": {"route": {"from_place": "A", "to_place": "B"}},
    }

    monkeypatch.setattr("app.broker.tasks.process_message", MagicMock())

    mock_session = MagicMock()
    monkeypatch.setattr(
        "app.broker.tasks.SessionLocal", MagicMock(return_value=mock_session)
    )

    mock_publish = MagicMock()
    monkeypatch.setattr("app.broker.tasks.event_publisher.task_ready", mock_publish)

    generate_pdf_task(request_data)

    mock_publish.assert_called_once()
    args, _ = mock_publish.call_args
    assert args[0] == "task-1"
    assert "api/pdf/download/task-1" in args[1]


def test_generate_pdf_task_publishes_failed_on_error(monkeypatch):
    request_data = {
        "request_id": f"task-{uuid.uuid4().hex[:8]}",
        "user_id": 1,
        "payload": {"route": {"from_place": "A", "to_place": "B"}},
    }
    monkeypatch.setattr(
        "app.broker.tasks.get_pdf_by_request_id", MagicMock(return_value=None)
    )
    monkeypatch.setattr(
        "app.broker.tasks.process_message",
        MagicMock(
            side_effect=PermanentError("Render error", client_message="Bad data")
        ),
    )
    monkeypatch.setattr("app.broker.tasks.SessionLocal", MagicMock())
    mock_task_failed = MagicMock()
    monkeypatch.setattr(
        "app.broker.tasks.event_publisher.task_failed", mock_task_failed
    )
    result = generate_pdf_task.apply(args=[request_data])
    assert result.failed() is True
    assert isinstance(result.result, PermanentError)
    mock_task_failed.assert_called_once()
    args, _ = mock_task_failed.call_args
    assert args[0] == request_data["request_id"]
    assert args[1] == "Bad data"


@pytest.mark.asyncio
async def test_event_consumer_reads_from_cache():
    mock_redis = AsyncMock()
    expected_data = {"status": "ready", "url": "http://test/download"}
    mock_redis.get.side_effect = [None, None, json.dumps(expected_data)]
    consumer = EventConsumer(client=mock_redis)
    result = await consumer.wait_for_result("test-id", max_attempts=5, time_sleep=0.01)
    assert result == expected_data
    expected_key = "task_updates:test-id"
    mock_redis.get.assert_called_with(expected_key)
    assert mock_redis.get.call_count == 3


@pytest.mark.asyncio
async def test_event_consumer_returns_none_on_timeout():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    consumer = EventConsumer(client=mock_redis)
    result = await consumer.wait_for_result("test-id", max_attempts=3, time_sleep=0.01)
    assert result is None
    assert mock_redis.get.call_count == 3
