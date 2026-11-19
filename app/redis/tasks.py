import logging

from app.db.database import SessionLocal
from app.publishers import event_publisher
from app.redis.worker import celery_app
from app.schemas.contracts import PdfRequest
from app.service.save import process_message
from config import settings

log = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, name="generate_tour_pdf")
def generate_pdf_task(self, request_data: dict):
    request = PdfRequest(**request_data)
    with SessionLocal() as db:
        try:
            process_message(db, request)
            url = f"{settings.url_prefix}api/pdf/download/{request.request_id}"
            event_publisher.task_ready(request.request_id, url)
            log.info(
                "Successfuly sent message with request_id: %s to Redis",
                request.request_id,
            )
            return {"status": "completed", "request_id": request.request_id}
        except Exception as exc:
            log.exception("Task failed", exc_info=exc)
            event_publisher.task_failed(request.request_id, str(exc))
            raise self.retry(countdown=2**self.request.retries)
