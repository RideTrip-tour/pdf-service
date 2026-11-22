from datetime import date
import logging

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.pdf_history import get_pdf_by_request_id, search_user_history
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

    def get_history(self, user_id: int, **filters) -> list[dict[str, str | date]]:
        """Returns list of trips for history (without bytes)."""
        pdf_files = search_user_history(self.session, user_id, **filters)
        result = []
        for pdf in pdf_files:
            extra = pdf.extra_data or {}
            route = extra.get("route", {})
            dates = extra.get("dates", {})
            activity = extra.get("activity", {})
            result.append({
                "request_id": pdf.request_id,
                "from_place": route.get("from_place"),
                "to_place": route.get("to_place"),
                "date_from": dates.get("date_from"),
                "date_to": dates.get("date_to"),
                "activity": activity.get("activity"),
                "created_at": pdf.created_at,
            })
        return result


def get_pdf_service(
    session: Session = Depends(get_session),
) -> PDFService:
    return PDFService(session)
