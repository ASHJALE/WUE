from fastapi import FastAPI, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from .database import check_database_connection


app = FastAPI(
    title="WUE API",
    description="AI-Assisted Furniture Material Estimation and Quotation System",
    version="1.0.0",
)


@app.get("/")
def home() -> dict[str, str]:
    """Confirm that the API process is running without requiring PostgreSQL."""
    return {
        "message": "Welcome to the WUE Backend API!",
        "status": "Running Successfully",
    }


@app.get("/health/database")
def database_health() -> dict[str, str]:
    """Verify that the configured PostgreSQL server accepts a simple query."""
    try:
        check_database_connection()
    except (RuntimeError, SQLAlchemyError):
        # Keep credentials and low-level database details out of API responses.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed. Check the backend configuration and server.",
        )

    return {"database": "connected"}
