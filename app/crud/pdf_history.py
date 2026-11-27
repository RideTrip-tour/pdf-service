from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import UserPDFHistory
from app.schemas.contracts import PdfRequest
from app.schemas.internal import TourExtraData
from app.exceptions import PermanentError


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
        query = query.where(
            UserPDFHistory.extra_data["route"]["from_place"].astext == from_place
        )
    if to_place:
        query = query.where(
            UserPDFHistory.extra_data["route"]["to_place"].astext == to_place
        )
    if date_from:
        query = query.where(
            UserPDFHistory.extra_data["dates"]["date_from"].astext >= date_from
        )
    if date_to:
        query = query.where(
            UserPDFHistory.extra_data["dates"]["date_to"].astext <= date_to
        )
    if activity:
        query = query.where(UserPDFHistory.extra_data["activity"].op("?")(activity))

    return list(session.execute(query).scalars().all())


def save_pdf_history(db: Session, request: PdfRequest, pdf_bytes: bytes) -> None:
    """Сохраняет сгенерированный PDF и метаданные в историю."""
    extra_data = TourExtraData(
        route=request.payload.route.model_dump() if request.payload.route else None,
        dates={
            "date_from": str(request.payload.dates.date_from)
            if request.payload.dates
            else None,
            "date_to": str(request.payload.dates.date_to)
            if request.payload.dates
            else None,
        },
        activity=[act for act in request.payload.activity]
        if request.payload.activity
        else None,
    )
    statement = (
        insert(UserPDFHistory)
        .values(
            user_id=request.user_id,
            request_id=request.request_id,
            extra_data=extra_data.to_dict(),
            file_data=pdf_bytes,
            created_at=datetime.now(UTC),
        )
        .on_conflict_do_nothing(index_elements=["request_id"])
    )
    db.execute(statement)
    db.commit()
