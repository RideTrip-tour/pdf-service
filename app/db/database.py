import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import settings


database_url = os.getenv("DATABASE_URL") or settings.DATABASE_URL

engine = create_engine(
    database_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_session():
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
