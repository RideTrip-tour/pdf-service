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
    monkeypatch.setattr(
        "app.broker.tasks.handle_generate_pdf",
        MagicMock(return_value={"status": "completed"}),
    )
    mock_task_processing = MagicMock()
    monkeypatch.setattr("app.broker.tasks.event_publisher.task_processing", mock_task_processing)
    mock_task_ready = MagicMock()
    monkeypatch.setattr("app.broker.tasks.event_publisher.task_ready", mock_task_ready)
    generate_pdf_task(request_data)
    mock_task_ready.assert_called_once()


def test_generate_pdf_task_publishes_failed_on_error(monkeypatch):
    request_data = {
        "request_id": f"task-{uuid.uuid4().hex[:8]}",
        "user_id": 1,
        "payload": {"route": {"from_place": "A", "to_place": "B"}},
    }
    monkeypatch.setattr(
        "app.broker.tasks.handle_generate_pdf",
        MagicMock(side_effect=PermanentError("Render error", "Bad data")),
    )
    mock_task_processing = MagicMock()
    monkeypatch.setattr("app.broker.tasks.event_publisher.task_processing", mock_task_processing)
    mock_task_failed = MagicMock()
    monkeypatch.setattr(
        "app.broker.tasks.event_publisher.task_failed", mock_task_failed
    )
    result = generate_pdf_task.apply(args=[request_data])
    assert result.failed() is True
    mock_task_failed.assert_called_once_with(request_data["request_id"], "Bad data")


@pytest.mark.asyncio
async def test_event_consumer_reads_from_cache():
    mock_redis = AsyncMock()
    expected_data = {"status": "ready", "url": "http://test/download"}
    mock_redis.get.side_effect = [None, None, json.dumps(expected_data)]
    consumer = EventConsumer(client=mock_redis)
    results = []
    async for item in consumer.wait_for_result(
        "test-id", max_attempts=5, time_sleep=0.01
    ):
        results.append(item)
    assert len(results) == 1
    assert results[0] == expected_data
    assert mock_redis.get.call_count == 3


@pytest.mark.asyncio
async def test_event_consumer_returns_none_on_timeout():
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    consumer = EventConsumer(client=mock_redis)
    results = []
    async for item in consumer.wait_for_result(
        "test-id", max_attempts=3, time_sleep=0.01
    ):
        results.append(item)
    assert len(results) == 1
    assert results[0]["status"] == "failed"
    assert results[0]["reason"] == "timeout"
