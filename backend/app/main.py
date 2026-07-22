from fastapi import FastAPI, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from .database import check_database_connection
from .routers.auth import router as auth_router
from .routers.estimates import router as estimates_router
from .routers.furniture_materials import router as furniture_materials_router
from .routers.furniture_types import router as furniture_types_router
from .routers.inventory import router as inventory_router
from .routers.materials import router as materials_router
from .routers.quotations import router as quotations_router
from .routers.quotation_actions import router as quotation_actions_router


app = FastAPI(
    title="WUE API",
    description="AI-Assisted Furniture Material Estimation and Quotation System",
    version="1.0.0",
)

app.include_router(furniture_types_router)
app.include_router(auth_router)
app.include_router(materials_router)
app.include_router(inventory_router)
app.include_router(furniture_materials_router)
app.include_router(estimates_router)
app.include_router(quotations_router)
app.include_router(quotation_actions_router)


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
