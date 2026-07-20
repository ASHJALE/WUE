"""Environment-based application configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv


# Always look for .env in backend/, regardless of the current terminal folder.
BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


def get_database_url() -> str:
    """Return the SQLAlchemy PostgreSQL URL or explain how to configure it."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy backend/.env.example to backend/.env "
            "and enter the PostgreSQL credentials."
        )

    if not database_url.startswith("postgresql+psycopg://"):
        raise RuntimeError(
            "DATABASE_URL must start with 'postgresql+psycopg://' so SQLAlchemy "
            "uses the installed Psycopg 3 driver."
        )

    return database_url
