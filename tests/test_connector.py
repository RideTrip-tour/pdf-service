from unittest.mock import MagicMock

import pytest

from app.publishers.connectors import CeleryConnector, PublishResult


def make_producer(task_id: str = "celery-task-123") -> MagicMock:
    producer = MagicMock()
    producer.send_task.return_value.id = task_id
    return producer


@pytest.mark.asyncio
async def test_publish_success_returns_result():
    producer = make_producer(task_id="abc-123")
    connector = CeleryConnector(producer=producer)

    result = await connector.publish(
        queue="pdf",
        task_name="app.redis.tasks.generate_pdf_task",
        args=[{"request_id": "req-1", "payload": {"route": {}}}],
    )

    assert isinstance(result, PublishResult)
    assert result.task_id == "abc-123"
    assert result.request_id == "req-1"
    producer.send_task.assert_called_once_with(
        "app.redis.tasks.generate_pdf_task",
        args=[{"request_id": "req-1", "payload": {"route": {}}}],
        kwargs={},
        queue="pdf",
    )


@pytest.mark.asyncio
async def test_publish_calls_send_task_in_thread():
    producer = make_producer()
    connector = CeleryConnector(producer=producer)

    called = {}

    async def fake_to_thread(func, *args, **kwargs):
        called["func"] = func
        called["args"] = args
        called["kwargs"] = kwargs
        return func(*args, **kwargs)

    import app.publishers.connectors as connectors_module

    original = connectors_module.asyncio.to_thread
    connectors_module.asyncio.to_thread = fake_to_thread
    try:
        await connector.publish(
            queue="pdf",
            task_name="app.redis.tasks.generate_pdf_task",
            args=[{"request_id": "req-1"}],
        )
    finally:
        connectors_module.asyncio.to_thread = original

    assert called["func"] == producer.send_task
    assert called["args"][0] == "app.redis.tasks.generate_pdf_task"
    assert called["kwargs"]["queue"] == "pdf"


@pytest.mark.asyncio
async def test_publish_raises_if_request_id_missing():
    producer = make_producer()
    connector = CeleryConnector(producer=producer)

    with pytest.raises(ValueError, match="request_id is required"):
        await connector.publish(
            queue="pdf",
            task_name="app.redis.tasks.generate_pdf_task",
            args=[{"payload": {"route": {}}}],
        )

    producer.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_publish_raises_if_args_empty():
    producer = make_producer()
    connector = CeleryConnector(producer=producer)

    with pytest.raises(ValueError, match="request_id is required"):
        await connector.publish(
            queue="pdf",
            task_name="app.redis.tasks.generate_pdf_task",
            args=[],
        )

    producer.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_publish_raises_if_args_none():
    producer = make_producer()
    connector = CeleryConnector(producer=producer)

    with pytest.raises(ValueError, match="request_id is required"):
        await connector.publish(
            queue="pdf",
            task_name="app.redis.tasks.generate_pdf_task",
            args=None,
        )

    producer.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_publish_raises_if_first_arg_not_dict():
    producer = make_producer()
    connector = CeleryConnector(producer=producer)

    with pytest.raises(ValueError, match="request_id is required"):
        await connector.publish(
            queue="pdf",
            task_name="app.redis.tasks.generate_pdf_task",
            args=["not-a-dict"],
        )

    producer.send_task.assert_not_called()


@pytest.mark.asyncio
async def test_publish_propagates_send_task_exception():
    producer = MagicMock()
    producer.send_task.side_effect = RuntimeError("redis down")
    connector = CeleryConnector(producer=producer)

    with pytest.raises(RuntimeError, match="redis down"):
        await connector.publish(
            queue="pdf",
            task_name="app.redis.tasks.generate_pdf_task",
            args=[{"request_id": "req-1"}],
        )


@pytest.mark.asyncio
async def test_publish_logs_and_reraises(caplog):
    import logging

    producer = MagicMock()
    producer.send_task.side_effect = RuntimeError("broker unavailable")
    connector = CeleryConnector(producer=producer)

    with caplog.at_level(logging.ERROR), pytest.raises(RuntimeError):
        await connector.publish(
            queue="pdf",
            task_name="app.redis.tasks.generate_pdf_task",
            args=[{"request_id": "req-1"}],
        )

    assert "Failed to publish" in caplog.text
    assert "app.redis.tasks.generate_pdf_task" in caplog.text
    assert "req-1" in caplog.text


@pytest.mark.asyncio
async def test_publish_works_with_kwargs_only():
    producer = make_producer()
    connector = CeleryConnector(producer=producer)

    with pytest.raises(ValueError, match="request_id is required"):
        await connector.publish(
            queue="pdf",
            task_name="app.redis.tasks.generate_pdf_task",
            args=[],
            kwargs={"request_id": "req-1"},
        )
