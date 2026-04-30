import logging

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=not settings.database_url.startswith("sqlite"),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> bool:
    from src.database import models  # noqa: F401

    try:
        Base.metadata.create_all(bind=engine)
        return True
    except SQLAlchemyError as exc:
        logger.warning("Database initialization skipped because the database is unavailable: %s", exc)
        return False
