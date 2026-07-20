"""SQLAlchemy engine configuration and database connectivity helpers."""

from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase

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


def check_database_connection() -> None:
    """Run a harmless query; an exception means PostgreSQL is unavailable."""
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))
