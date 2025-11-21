"""Database session utilities"""
from contextlib import contextmanager
from sqlalchemy.orm import Session
from app.db.database import get_session


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_session() as db:
            # Use db session
            pass
    """
    session_gen = get_session()
    db = next(session_gen)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
