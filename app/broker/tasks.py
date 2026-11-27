import logging

from sqlalchemy.exc import OperationalError

from app.broker.worker import celery_app
from app.constants import DOWNLOAD_URL, TASK_NAME
from app.crud.pdf_history import get_pdf_by_request_id
from app.db.database import SessionLocal
from app.exceptions import PermanentError
from app.publishers import event_publisher
from app.schemas.contracts import PdfRequest
from app.service.save import process_message
from config import settings

log = logging.getLogger(__name__)

RETRYABLE_EXCEPTIONS = (OperationalError, ConnectionError, TimeoutError)


@celery_app.task(bind=True, max_retries=3, name=TASK_NAME)
def generate_pdf_task(self, request_data: dict):
    request = PdfRequest(**request_data)
    with SessionLocal() as db:
        try:
            existing_pdf = get_pdf_by_request_id(db, request.request_id)
            if existing_pdf:
                log.info(
                    "PDF with request_id: %s already exists, skipping",
                    request.request_id,
                )
            else:
                process_message(db, request)
                log.info(
                    "Successfuly sent message with request_id: %s to Redis",
                    request.request_id,
                )
            event_publisher.task_ready(
                request.request_id,
                DOWNLOAD_URL.format(
                    url_prefix=settings.url_prefix, request_id=request.request_id
                ),
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
            log.exception("Task failed")
            event_publisher.task_failed(request.request_id, exc.client_message)
            raise
        except Exception:
            log.exception("Unexpected error")
            event_publisher.task_failed(request.request_id, "Внутренняя ошибка сервера")
            raise
