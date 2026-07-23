"""Schemas for the non-persistent Phase 7.5 structured BOM generator."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.material import FurnitureRecommendationType, MaterialRecommendation


class BOMGenerateRequest(BaseModel):
    furniture_type: FurnitureRecommendationType
    materials: list[MaterialRecommendation] = Field(min_length=1)

    @model_validator(mode="after")
    def require_primary_material(self):
        if not any(material.priority == "Primary" for material in self.materials):
            raise ValueError("At least one Primary material recommendation is required.")
        return self


class GeneratedBOMItem(BaseModel):
    component: str = Field(min_length=1)
    recommended_material: str = Field(min_length=1)
    category: str = Field(min_length=1)
    source: Literal["Primary Recommendation", "Alternative Recommendation"]
    unit: str = Field(min_length=1)
    quantity: None = None
    notes: Literal["Quantity calculated in Phase 7.6"] = "Quantity calculated in Phase 7.6"


class BOMGenerateResponse(BaseModel):
    furniture_type: FurnitureRecommendationType
    display_name: str
    components: list[GeneratedBOMItem]
    status: Literal["generated"] = "generated"
