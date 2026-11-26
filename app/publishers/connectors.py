import asyncio
import json
import logging
from typing import Protocol

import redis
from celery import Celery
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PublishResult(BaseModel):
    task_id: str
    request_id: str


class BaseConnector(Protocol):
    async def publish(
        self,
        queue: str,
        task_name: str,
        args: list | None = None,
        kwargs: dict | None = None,
    ) -> PublishResult: ...


class CeleryConnector:
    def __init__(self, producer: Celery):
        self._producer = producer

    async def publish(
        self,
        queue: str,
        task_name: str,
        args: list | None = None,
        kwargs: dict | None = None,
    ) -> PublishResult:
        args = args or []
        kwargs = kwargs or {}
        request_id = None
        if kwargs and isinstance(kwargs.get("request_data"), dict):
            request_id = kwargs["request_data"].get("request_id")
        if not request_id and args and isinstance(args[0], dict):
            request_id = args[0].get("request_id")
        if not request_id:
            raise ValueError("request_id is required")
        try:
            result = await asyncio.to_thread(
                self._producer.send_task,
                task_name,
                args=args,
                kwargs=kwargs,
                queue=queue,
                task_id=request_id,
            )
            return PublishResult(task_id=str(result.id), request_id=str(request_id))
        except Exception:
            logger.exception(
                "Failed to publish %s to queue %s with request_id %s",
                task_name,
                queue,
                request_id,
            )
            raise


class RedisEventConnector:
    def __init__(self, client: redis.Redis):
        self._client = client

    def publish_event(self, channel: str, payload: dict):
        self._client.publish(channel, json.dumps(payload))
