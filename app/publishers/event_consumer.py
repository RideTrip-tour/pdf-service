import asyncio
import json
import logging
from collections.abc import AsyncIterator

import redis.asyncio as aioredis

from app.constants import CHANNEL

log = logging.getLogger(__name__)


class EventConsumer:
    def __init__(self, client: aioredis.Redis):
        self._client = client

    async def wait_for_result(
        self, request_id: str, max_attempts: int = 30, time_sleep: float = 1.0
    ) -> AsyncIterator[dict | None]:
        """Looks for the result in the cache, 30 attempts with 1.0 sec delay = 30 seconds."""
        latest_payload = None
        for _ in range(max_attempts):
            data = await self._client.get(CHANNEL.format(request_id=request_id))
            if data:
                payload = json.loads(data)
                if payload != latest_payload:
                    yield payload
                    latest_payload = payload
                if payload.get("status") in ("ready", "failed"):
                    return
            await asyncio.sleep(time_sleep)
        yield {"status": "failed", "reason": "timeout"}
