"""Database engine and session management for Watchtower."""

from collections.abc import Generator
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from watchtower.config import get_settings
from watchtower.db.models import Base

_engine: Optional[Engine] = None
_SessionFactory: Optional[sessionmaker[Session]] = None


def get_engine(db_url: Optional[str] = None) -> Engine:
    """Get or create SQLAlchemy engine singleton."""
    global _engine, _SessionFactory
    if _engine is None or db_url is not None:
        url = db_url or get_settings().DATABASE_URL
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
        _engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
        _SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_session_factory(db_url: Optional[str] = None) -> sessionmaker[Session]:
    """Get or create the session factory."""
    global _SessionFactory
    if _SessionFactory is None or db_url is not None:
        get_engine(db_url)
    assert _SessionFactory is not None
    return _SessionFactory


def get_db_session() -> Generator[Session, None, None]:
    """Provide a transactional database session scope."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def init_db(db_url: Optional[str] = None) -> None:
    """Create all tables in the database."""
    engine = get_engine(db_url)
    Base.metadata.create_all(bind=engine)
