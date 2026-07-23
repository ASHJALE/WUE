"""Schemas for preliminary, non-persistent BOM quantity estimates."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.bom import GeneratedBOMItem
from app.schemas.material import FurnitureRecommendationType

QuantityUnit = Literal["board_foot", "square_meter", "meter", "piece", "set", "application"]


class FurnitureDimensions(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    width: float = Field(gt=0)
    depth: float = Field(gt=0)
    height: float = Field(gt=0)


class QuantityEstimateRequest(BaseModel):
    furniture_type: FurnitureRecommendationType
    dimensions: FurnitureDimensions
    components: list[GeneratedBOMItem] = Field(min_length=1)


class EstimatedQuantityItem(BaseModel):
    component: str = Field(min_length=1)
    material: str = Field(min_length=1)
    category: str = Field(min_length=1)
    estimated_quantity: float = Field(gt=0)
    unit: QuantityUnit
    calculation_basis: Literal["Template Estimate"] = "Template Estimate"
    confidence: Literal["Preliminary"] = "Preliminary"


class QuantityEstimateResponse(BaseModel):
    furniture_type: FurnitureRecommendationType
    display_name: str
    components: list[EstimatedQuantityItem]
    status: Literal["estimated"] = "estimated"
