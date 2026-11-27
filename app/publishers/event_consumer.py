import asyncio
import json
import logging

import redis.asyncio as aioredis

from app.constants import CHANNEL

log = logging.getLogger(__name__)


class EventConsumer:
    def __init__(self, client: aioredis.Redis):
        self._client = client

    async def wait_for_result(
        self, request_id: str, max_attempts: int = 30, time_sleep: float = 1.0
    ) -> dict | None:
        """Looks for the result in the cache, 30 attempts with 1.0 sec delay = 30 seconds."""
        for _ in range(max_attempts):
            data = await self._client.get(CHANNEL.format(request_id=request_id))
            if data:
                return json.loads(data)
            await asyncio.sleep(time_sleep)
        return None
