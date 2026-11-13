import logging

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.pdf import get_pdf_by_request_id, search_user_history
from app.db.database import get_session

log = logging.getLogger(__name__)


class PDFService:
    def __init__(self, session: Session):
        self.session = session

    def download_pdf(self, request_id: str) -> bytes:
        """Get bytes from DB or raise 404."""
        pdf_file = get_pdf_by_request_id(self.session, request_id)
        if not pdf_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found"
            )
        return pdf_file.file_data

    def get_history(self, user_id: int, **filters):
        """Returns list of trips for history (without bytes)."""
        pdf_files = search_user_history(self.session, user_id, **filters)
        return [
            {
                "request_id": pdf_file.request_id,
                "from_place": pdf_file.from_place,
                "to_place": pdf_file.to_place,
                "date_from": pdf_file.date_from,
                "date_to": pdf_file.date_to,
                "activity": pdf_file.activity,
                "created_at": pdf_file.created_at,
            }
            for pdf_file in pdf_files
        ]


def get_pdf_service(
    session: Session = Depends(get_session),
) -> PDFService:
    return PDFService(session)
