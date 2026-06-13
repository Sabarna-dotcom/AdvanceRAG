# src/database/connection.py
"""
SQLAlchemyengine + session factory for PostgreSQL.

Usage (FastAPIdependency):
 from src.database.connectionimport get_db
 async def my_route(db=Depends(get_db)): ...

Usage (direct):
 from src.database.connectionimport get_session_factory
 SessionLocal= get_session_factory()
 with SessionLocal() as session:
 ...
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from src.config.settings import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ==========================================
# Declarative Base — shared by all models
# ==========================================

Base = declarative_base()


# ==========================================
# Engine + Session Factory (singletons)
# ==========================================

_engine = None
_SessionLocal= None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True, # auto-reconnect on stale connections
            pool_recycle=3600, # recycle connections every hour
        )
        logger.info("PostgreSQL engine created.")
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal= sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=get_engine(),
    )
    return _SessionLocal


# ==========================================
# FastAPIDependency
# ==========================================

def get_db() -> Generator:
    """
    FastAPIdependency — yields a database session per request.
    Always closes the session after the request, even on error.
    """
    SessionLocal= get_session_factory()
    db= SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==========================================
# Context Manager (for non-FastAPIuse)
# ==========================================

@contextmanager
def get_db_context():
    """
    Context manager for direct use outside FastAPI.

    Usage:
    with get_db_context() as db:
    db.query(User).all()
    """
    SessionLocal= get_session_factory()
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ==========================================
# Health check
# ==========================================

def check_connection() -> bool:
    """Quick connectivity check. Returns True if PostgreSQL is reachable."""
    try:
        with get_db_context() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"PostgreSQLconnection check failed: {e}")
        return False
