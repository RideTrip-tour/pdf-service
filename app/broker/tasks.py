import logging

from sqlalchemy.exc import OperationalError, IntegrityError
from pydantic import ValidationError

from app.broker.worker import celery_app
from app.db.database import SessionLocal
from app.publishers import event_publisher
from app.schemas.contracts import PdfRequest
from app.service.save import process_message
from config import settings
from app.constants import TASK_NAME
from app.exceptions import PermanentError
from app.crud.pdf_history import get_pdf_by_request_id

log = logging.getLogger(__name__)

RETRYABLE_EXCEPTIONS = (
    OperationalError,
    ConnectionError,
    TimeoutError
)

@celery_app.task(bind=True, max_retries=3, name=TASK_NAME)
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
        except RETRYABLE_EXCEPTIONS as exc:
            log.warning("Temporary error: %s, retrying", exc)
            if self.request.retries < self.max_retries:
                event_publisher.task_processing(
                    request.request_id,
                    f"Retry {self.request.retries + 1}/{self.max_retries}: {exc!s}",
                )
            raise self.retry(countdown=2**self.request.retries)
        except PermanentError as exc:
            log.error("Task failed", exc.message, exc_info=True)
            event_publisher.task_failed(request.request_id, exc.client_message)
            raise
        except Exception as exc:
            log.exception("Unexpected error", exc)
            event_publisher.task_failed(request.request_id, "Внутренняя ошибка сервера")
            raise
