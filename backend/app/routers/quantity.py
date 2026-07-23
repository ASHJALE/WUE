"""Authenticated preliminary BOM quantity estimation endpoint."""

from fastapi import APIRouter, HTTPException, status

from app.dependencies.auth import CurrentUser
from app.schemas.quantity import QuantityEstimateRequest, QuantityEstimateResponse
from app.services.material_recommender import DISPLAY_NAMES
from app.services.quantity_estimator import UnsupportedBOMComponentError, estimate_quantities

router = APIRouter(prefix="/bom", tags=["BOM Quantity Estimation"])


@router.post("/estimate-quantities", response_model=QuantityEstimateResponse)
def estimate_bom_quantities(
    data: QuantityEstimateRequest,
    _current_user: CurrentUser,
) -> QuantityEstimateResponse:
    try:
        components = estimate_quantities(data.furniture_type, data.dimensions, data.components)
    except UnsupportedBOMComponentError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    return QuantityEstimateResponse(
        furniture_type=data.furniture_type,
        display_name=DISPLAY_NAMES[data.furniture_type],
        components=components,
    )
