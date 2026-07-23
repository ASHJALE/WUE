"""Authenticated, non-persistent structured BOM generation endpoint."""

from fastapi import APIRouter

from app.dependencies.auth import CurrentUser
from app.schemas.bom import BOMGenerateRequest, BOMGenerateResponse
from app.services.bom_generator import generate_bom
from app.services.material_recommender import DISPLAY_NAMES

router = APIRouter(prefix="/bom", tags=["BOM Generation"])


@router.post("/generate", response_model=BOMGenerateResponse)
def generate_structured_bom(
    data: BOMGenerateRequest,
    _current_user: CurrentUser,
) -> BOMGenerateResponse:
    return BOMGenerateResponse(
        furniture_type=data.furniture_type,
        display_name=DISPLAY_NAMES[data.furniture_type],
        components=generate_bom(data.furniture_type, data.materials),
    )
