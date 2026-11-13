import logging
import time

from sqlalchemy.orm import Session

from app.schemas.contracts import PdfRequest
from app.crud.pdf import save_pdf_history
from app.service.renderer import render_tour_pdf
from app.service.sanitize import sanitize_payload

log = logging.getLogger(__name__)

logging.getLogger("weasyprint").setLevel(logging.WARNING)
logging.getLogger("fontTools").setLevel(logging.WARNING)
logging.getLogger("fontTools.subset").setLevel(logging.WARNING)


def process_message(db: Session, request: PdfRequest) -> bool:
    clean_request = sanitize_payload(request.payload)
    render_start = time.time()
    pdf_bytes = render_tour_pdf(clean_request)
    log.info(
        f"TIMING: [{request.request_id}] Рендер занял {time.time() - render_start:.3f} сек"
    )
    save_pdf_history(db, request, pdf_bytes)
    log.info(f"TIMING: [{request.request_id}] Сохранено в БД")
    return True
