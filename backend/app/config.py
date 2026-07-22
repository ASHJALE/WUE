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


def get_jwt_secret_key() -> str:
    """Return the JWT signing key, with a documented local-only fallback."""
    return os.getenv(
        "JWT_SECRET_KEY",
        "wue-development-only-secret-change-before-production",
    )


def get_jwt_algorithm() -> str:
    """Return the configured symmetric JWT signing algorithm."""
    return os.getenv("JWT_ALGORITHM", "HS256")


def get_jwt_expiration_minutes() -> int:
    """Return and validate the access-token lifetime."""
    raw_value = os.getenv("JWT_EXPIRATION_MINUTES", "60")
    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError("JWT_EXPIRATION_MINUTES must be an integer.") from error
    if value <= 0:
        raise RuntimeError("JWT_EXPIRATION_MINUTES must be greater than zero.")
    return value
