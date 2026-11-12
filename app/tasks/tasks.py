import json

import logging
from celery import shared_task

from app.tasks.worker import celery_app
from app.db.database import SessionLocal
from app.schemas.contracts import PdfRequest
from app.service.save import process_message
from app.core.redis import sync_redis

log = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def generate_pdf_task(self, request_data: dict):
    """Process a data item in the background with retry logic."""
    request = PdfRequest(**request_data)
    db = SessionLocal()
    try:
        process_message(db, request)
        message = {
            "request_id": request.request_id,
            "status": "ready",
            "url": f"http://localhost:8000/api/pdf/download/{request.request_id}"
        }
        log.info(f"Отправляю в Redis канал task_updates:{request.request_id} сообщение: {message}")
        sync_redis.publish(f"task_updates:{request.request_id}", json.dumps(message))
        return {"status": "completed", "request_id": request.request_id}
    except Exception as exc:
        message = {
            "request_id": request.request_id,
            "status": "failed",
            "reason": str(exc)
        }
        sync_redis.publish(f"task_updates:{request.request_id}", json.dumps(message))
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        db.close()


@celery_app.task
def send_notification(user_id: int, message: str):
    """Send a notification to a user asynchronously."""
    # Your notification logic here
    return {"sent_to": user_id, "message": message}
