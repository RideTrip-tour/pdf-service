from datetime import datetime

from sqlalchemy.orm import Session

from app.schemas.contracts import PdfRequest
from app.db.models import UserPDFHistory
from sqlalchemy import select
from sqlalchemy.orm import Session


def get_pdf_by_request_id(session: Session, request_id: str) -> UserPDFHistory | None:
    return session.execute(
        select(UserPDFHistory).where(UserPDFHistory.request_id == request_id)
    ).scalar_one_or_none()


def search_user_history(
    session: Session,
    user_id: int,
    from_place: str | None = None,
    to_place: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    activity: str | None = None,
) -> list[UserPDFHistory]:
    """Searches trips in user's history with filters."""
    query = select(UserPDFHistory).where(UserPDFHistory.user_id == user_id)

    if from_place:
        query = query.where(UserPDFHistory.from_place == from_place)
    if to_place:
        query = query.where(UserPDFHistory.to_place == to_place)
    if date_from:
        query = query.where(UserPDFHistory.date_from == date_from)
    if date_to:
        query = query.where(UserPDFHistory.date_to == date_to)
    if activity:
        query = query.where(UserPDFHistory.activity.like(f"%{activity}%"))

    return list(session.execute(query).scalars().all())


def save_pdf_history(db: Session, request: PdfRequest, pdf_bytes: bytes) -> None:
    """Сохраняет сгенерированный PDF и метаданные в историю."""
    payload = request.payload

    from_place = payload.route.from_place if payload.route else None
    to_place = payload.route.to_place if payload.route else None
    date_from = payload.dates.date_from if payload.dates else None
    date_to = payload.dates.date_to if payload.dates else None
    activity = ", ".join(payload.activity) if payload.activity else None

    record = UserPDFHistory(
        user_id=request.user_id,
        request_id=request.request_id,
        from_place=from_place,
        to_place=to_place,
        date_from=date_from,
        date_to=date_to,
        activity=activity,
        file_data=pdf_bytes,
        created_at=datetime.now(),
    )
    db.add(record)
    db.commit()
