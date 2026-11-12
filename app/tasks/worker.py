# Celery application setup with Redis broker
from celery import Celery
from app.config import settings

celery_app = Celery(
    "worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.tasks"]
)

# Configure task serialization and result expiration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
)

# Auto-discover tasks in the app.tasks module
celery_app.autodiscover_tasks(["app"])
