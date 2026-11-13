import logging

from sqlalchemy.orm import Session

from app.schemas.contracts import PdfRequest
from app.crud.pdf import save_pdf_history
from app.service.renderer import render_tour_pdf
from app.service.sanitize import sanitize_payload


def process_message(db: Session, request: PdfRequest) -> bool:
    clean_request = sanitize_payload(request.payload)
    pdf_bytes = render_tour_pdf(clean_request)
    save_pdf_history(db, request, pdf_bytes)
    return True
