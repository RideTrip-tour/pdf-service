import redis
import redis.asyncio as aioredis
from config import settings

sync_redis = redis.from_url(
    settings.redis_url,
    decode_responses=True
)

async_redis = aioredis.from_url(
    settings.redis_url,
    decode_responses=True
)
