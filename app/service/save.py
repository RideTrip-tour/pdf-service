from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError, IntegrityError

from app.crud.pdf_history import save_pdf_history
from app.schemas.contracts import PdfRequest
from app.service.renderer import render_tour_pdf
from app.service.sanitize import sanitize_payload
from app.exceptions import PermanentError


def process_message(db: Session, request: PdfRequest) -> bool:
    """Очищает request от опасных тегов, генерит ПДФ и сохраняет в БД."""
    clean_request = sanitize_payload(request.payload)
    try:
        pdf_bytes = render_tour_pdf(clean_request)
    except Exception as exc:
        raise PermanentError(
            message=f"Render failed: {exc}",
            client_message="Could't generate PDF. Make sure the data is correct."
        ) from exc
    save_pdf_history(db, request, pdf_bytes)
    return True
