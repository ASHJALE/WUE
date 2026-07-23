"""Authenticated non-persistent preliminary cost endpoint."""

from fastapi import APIRouter, HTTPException, status

from app.dependencies.auth import CurrentUser
from app.schemas.cost import CostCalculateRequest, CostCalculateResponse
from app.services.cost_calculator import UnsupportedMaterialPriceError, calculate_preliminary_cost

router = APIRouter(prefix="/costs", tags=["Preliminary Costs"])


@router.post("/calculate", response_model=CostCalculateResponse)
def calculate_costs(
    data: CostCalculateRequest,
    _current_user: CurrentUser,
) -> CostCalculateResponse:
    try:
        return calculate_preliminary_cost(data)
    except UnsupportedMaterialPriceError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
