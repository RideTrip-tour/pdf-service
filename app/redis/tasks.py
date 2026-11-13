import json

import logging

from app.redis.worker import celery_app
from app.db.database import SessionLocal
from app.schemas.contracts import PdfRequest
from app.service.save import process_message
from app.redis.redis import sync_redis
from config import settings

log = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def generate_pdf_task(self, request_data: dict):
    request = PdfRequest(**request_data)
    db = SessionLocal()
    try:
        process_message(db, request)
        message = {
            "request_id": request.request_id,
            "status": "ready",
            "url": f"{settings.url_prefix}api/pdf/download/{request.request_id}"
        }
        sync_redis.publish(f"task_updates:{request.request_id}", json.dumps(message))
        log.info("Successfuly sent message with request_id: %s to Redis", request.request_id)
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
