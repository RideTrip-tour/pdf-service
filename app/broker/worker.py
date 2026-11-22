import logging

from celery import Celery
from kombu import Exchange, Queue

from config import settings

logging.getLogger("weasyprint").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)
logging.getLogger("fontTools.subset").setLevel(logging.WARNING)
logging.getLogger("ForkPoolWorker-4").setLevel(logging.WARNING)


celery_app = Celery(
    "pdf_service_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.broker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    task_queues=(Queue("pdf", Exchange("pdf"), routing_key="pdf"),),
    task_default_queue="pdf",
    task_default_exchange="pdf",
    task_default_routing_key="pdf",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 600},
)
