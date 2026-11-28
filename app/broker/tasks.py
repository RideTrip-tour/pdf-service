import logging

from sqlalchemy.exc import OperationalError

from app.broker.handlers import handle_generate_pdf
from app.broker.worker import celery_app
from app.constants import DOWNLOAD_URL, TASK_NAME
from app.exceptions import PermanentError
from app.publishers import event_publisher
from app.schemas.contracts import PdfRequest
from config import settings

log = logging.getLogger(__name__)

RETRYABLE_EXCEPTIONS = (OperationalError, ConnectionError, TimeoutError)


@celery_app.task(bind=True, max_retries=3, name=TASK_NAME)
def generate_pdf_task(self, request_data: dict):
    request = PdfRequest(**request_data)
    event_publisher.task_processing(request.request_id, "Preparing data...")
    try:
        event_publisher.task_processing(request.request_id, "Rendering the document...")
        result = handle_generate_pdf(request)
        event_publisher.task_processing(request.request_id, "Finalizing...")
        event_publisher.task_ready(
            request.request_id,
            DOWNLOAD_URL.format(
                url_prefix=settings.url_prefix, request_id=request.request_id
            ),
        )
        return result
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
