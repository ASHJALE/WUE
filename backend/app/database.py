"""SQLAlchemy engine configuration and database connectivity helpers."""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_database_url


class Base(DeclarativeBase):
    """Shared declarative base for WUE ORM models."""

    pass


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Create one reusable connection pool for the application process."""
    return create_engine(
        get_database_url(),
        # Check pooled connections before use so stale connections are replaced.
        pool_pre_ping=True,
    )


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return the shared factory used for request-scoped database sessions."""
    return sessionmaker(
        bind=get_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


def get_db() -> Generator[Session, None, None]:
    """Provide one SQLAlchemy session per FastAPI request and always close it."""
    with get_session_factory()() as session:
        yield session


def check_database_connection() -> None:
    """Run a harmless query; an exception means PostgreSQL is unavailable."""
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
