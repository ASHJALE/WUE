"""Environment-based application configuration."""

import os
from dataclasses import dataclass
from functools import lru_cache
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


def _environment_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name, str(default)).strip().lower()
    if raw_value not in {"true", "false"}:
        raise RuntimeError(f"{name} must be either true or false.")
    return raw_value == "true"


@dataclass(frozen=True)
class ClassifierSettings:
    enabled: bool
    backend: str
    model_path: Path
    version: str
    min_confidence: float
    output_is_logits: bool
    development_fallback: bool


@lru_cache(maxsize=1)
def get_classifier_settings() -> ClassifierSettings:
    """Return validated local classifier configuration without exposing its path."""
    backend = os.getenv("FURNITURE_MODEL_BACKEND", "onnx").strip().lower()
    if backend != "onnx":
        raise RuntimeError("FURNITURE_MODEL_BACKEND must be 'onnx'.")
    raw_path = Path(
        os.getenv("FURNITURE_MODEL_PATH", "models/furniture_classifier.onnx")
    )
    if raw_path.is_absolute():
        raise RuntimeError("FURNITURE_MODEL_PATH must be relative to backend/.")
    model_path = (BACKEND_DIR / raw_path).resolve()
    model_directory = (BACKEND_DIR / "models").resolve()
    if model_directory not in model_path.parents:
        raise RuntimeError("FURNITURE_MODEL_PATH must stay inside backend/models/.")
    try:
        min_confidence = float(os.getenv("FURNITURE_MIN_CONFIDENCE", "0.50"))
    except ValueError as error:
        raise RuntimeError("FURNITURE_MIN_CONFIDENCE must be numeric.") from error
    if not 0 <= min_confidence <= 1:
        raise RuntimeError("FURNITURE_MIN_CONFIDENCE must be between zero and one.")
    return ClassifierSettings(
        enabled=_environment_bool("FURNITURE_CLASSIFIER_ENABLED", True),
        backend=backend,
        model_path=model_path,
        version=os.getenv("FURNITURE_MODEL_VERSION", "uninstalled").strip() or "uninstalled",
        min_confidence=min_confidence,
        output_is_logits=_environment_bool("FURNITURE_MODEL_OUTPUT_IS_LOGITS", True),
        development_fallback=_environment_bool(
            "FURNITURE_DEVELOPMENT_FALLBACK_ENABLED", False
        ),
    )
