import redis
import redis.asyncio as aioredis
from app.config import settings

# Синхронный клиент (для Celery-воркера)
sync_redis = redis.from_url(
    settings.redis_url,
    decode_responses=True
)

# Асинхронный клиент (для FastAPI/SSE)
async_redis = aioredis.from_url(
    settings.redis_url,
    decode_responses=True
)