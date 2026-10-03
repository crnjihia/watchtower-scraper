import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from .models import Base

DATABASE_URL = os.getenv("SQLITE_DB_PATH", "sqlite:///angalia.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
ScopedSession = scoped_session(SessionFactory)


def init_db(target_engine=None):
    """Create all tables in the database."""
    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)


# Automatically initialize default tables on import
try:
    init_db()
except Exception:
    pass



@contextmanager
def get_session(custom_session=None):
    """Context manager yielding a SQLAlchemy session."""
    if custom_session is not None:
        yield custom_session
        return

    session = ScopedSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
