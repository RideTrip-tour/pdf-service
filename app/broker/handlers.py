import logging

from app.crud.pdf_history import get_pdf_by_request_id
from app.db.database import SessionLocal
from app.schemas.contracts import PdfRequest
from app.service.save import process_message

log = logging.getLogger(__name__)


def handle_generate_pdf(request: PdfRequest) -> dict:
    with SessionLocal() as db:
        existing_pdf = get_pdf_by_request_id(db, request.request_id)
        if existing_pdf:
            log.info(
                "PDF with request_id: %s already exists, skipping",
                request.request_id,
            )
            return {"status": "completed", "request_id": request.request_id}
        else:
            process_message(db, request)
            log.info(
                "Successfuly sent message with request_id: %s to Redis",
                request.request_id,
            )
            return {"status": "completed", "request_id": request.request_id}
