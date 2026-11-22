from datetime import date, datetime

from sqlalchemy import Date, DateTime, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


class UserPDFHistory(Base):
    __tablename__ = "user_pdf_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(nullable=True)
    request_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    file_data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
