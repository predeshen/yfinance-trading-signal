"""Database connection and session management"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

Base = declarative_base()

# Global engine and session maker
_engine = None
_SessionLocal = None


def init_database(database_url: str) -> None:
    """
    Initialize database engine and session maker.
    
    Args:
        database_url: PostgreSQL connection URL
    """
    global _engine, _SessionLocal
    
    _engine = create_engine(
        database_url,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=5,
        max_overflow=10,
    )
    
    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine
    )


def get_engine():
    """Get database engine"""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _engine


def get_session() -> Generator[Session, None, None]:
    """
    Get database session.
    
    Yields:
        Database session
    """
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables() -> None:
    """Create all tables (for testing purposes)"""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    Base.metadata.create_all(bind=_engine)


def drop_all_tables() -> None:
    """Drop all tables (for testing purposes)"""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    Base.metadata.drop_all(bind=_engine)
