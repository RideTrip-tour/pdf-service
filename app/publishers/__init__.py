import redis
import redis.asyncio as aioredis

from app.broker.worker import celery_app
from app.publishers.connectors import CeleryConnector, RedisEventConnector
from app.publishers.event_publisher import EventPublisher
from app.publishers.task_publisher import TaskPublisher
from app.publishers.event_consumer import EventConsumer
from config import settings

celery_connector = CeleryConnector(producer=celery_app)
task_publisher = TaskPublisher(connector=celery_connector)

sync_redis_client = redis.from_url(settings.redis_url, decode_responses=True)
redis_event_connector = RedisEventConnector(client=sync_redis_client)
event_publisher = EventPublisher(connector=redis_event_connector)

async_redis_client = aioredis.from_url(settings.redis_url, decode_responses=False)
event_consumer = EventConsumer(client=async_redis_client)
